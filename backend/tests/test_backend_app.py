from uuid import UUID

from dishka import Provider, Scope, provide
from fakes.browser_repository import InMemoryBrowserRepository
from fakes.lease_store import InMemoryLeaseStore
from fakes.session_repositories import (
    InMemoryAuthenticationProfileRepository,
    InMemoryBrowserCheckpointRepository,
    InMemorySessionRepository,
)
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.domain.models import Browser, BrowserSlot
from backend.features.browsers.infrastructure import BrowserProvider
from backend.features.leases.infrastructure import LeaseProvider
from backend.features.sessions.application.ports import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    BrowserRuntime,
    SessionRepository,
)
from backend.features.sessions.domain.models import (
    AuthenticationStateDocument,
    BrowserStateDocument,
    Download,
)
from backend.features.sessions.infrastructure.settings import SessionSettings

OWNER_ID = str(UUID(int=7))
TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


class FakeProvisioner(BrowserProvisioner):
    def __init__(self) -> None:
        self.started: list[UUID] = []
        self.released: list[UUID] = []

    async def provision(self) -> tuple[BrowserSlot, ...]:
        return (
            BrowserSlot(
                UUID(int=1),
                "http://worker-1",
            ),
        )

    async def deprovision(self) -> None:
        pass

    async def start(self, slot: BrowserSlot) -> None:
        self.started.append(slot.id)

    async def release(self, slot: BrowserSlot) -> None:
        self.released.append(slot.id)


class FakeBrowserRuntime(BrowserRuntime):
    """Keep the captured document, the way a worker would hand it back."""

    def __init__(self) -> None:
        self.mounted_authentication: AuthenticationStateDocument | None = None
        self.mounted_browser: BrowserStateDocument | None = None

    async def capture_authentication(
        self, browser: Browser
    ) -> AuthenticationStateDocument:
        return {"cookies": [], "localStorage": []}

    async def mount_authentication(
        self, browser: Browser, state: AuthenticationStateDocument
    ) -> None:
        self.mounted_authentication = state

    async def capture_browser(self, browser: Browser) -> BrowserStateDocument:
        return {
            "tabs": [
                {
                    "url": "https://example.com/inbox",
                    "scroll": {"x": 0, "y": 0},
                    "sessionStorage": [],
                }
            ],
            "active_tab_index": 0,
        }

    async def mount_browser(
        self, browser: Browser, state: BrowserStateDocument
    ) -> None:
        self.mounted_browser = state

    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]:
        return ()

    async def clear_downloads(self, browser: Browser) -> None:
        return None

    async def download_file(self, browser: Browser, download_id: str) -> bytes:
        raise AssertionError("No fake download exists")


class FakeSessionProvider(Provider):
    def __init__(
        self,
        sessions: SessionRepository,
        browser_runtime: BrowserRuntime,
        checkpoints: BrowserCheckpointRepository,
        authentication_profiles: AuthenticationProfileRepository,
    ) -> None:
        super().__init__()
        self._sessions = sessions
        self._browser_runtime = browser_runtime
        self._checkpoints = checkpoints
        self._authentication_profiles = authentication_profiles

    @provide(scope=Scope.APP)
    def settings(self) -> SessionSettings:
        return SessionSettings(authentication_state_encryption_key=TEST_ENCRYPTION_KEY)

    @provide(scope=Scope.REQUEST, provides=SessionRepository)
    def sessions(self) -> SessionRepository:
        return self._sessions

    @provide(scope=Scope.APP, provides=BrowserRuntime)
    def browser_runtime(self) -> BrowserRuntime:
        return self._browser_runtime

    @provide(scope=Scope.REQUEST, provides=BrowserCheckpointRepository)
    def checkpoints(self) -> BrowserCheckpointRepository:
        return self._checkpoints

    @provide(scope=Scope.REQUEST, provides=AuthenticationProfileRepository)
    def authentication_profiles(self) -> AuthenticationProfileRepository:
        return self._authentication_profiles


def create_test_app(
    provisioner: BrowserProvisioner,
    repository: InMemoryBrowserRepository,
    sessions: InMemorySessionRepository,
    browser_state: BrowserRuntime,
    checkpoints: InMemoryBrowserCheckpointRepository | None = None,
    authentication_profiles: InMemoryAuthenticationProfileRepository
    | None = None,
):
    return create_app(
        (
            BrowserProvider(provisioner, repository),
            LeaseProvider(InMemoryLeaseStore()),
            FakeSessionProvider(
                sessions=sessions,
                browser_runtime=browser_state,
                checkpoints=checkpoints or InMemoryBrowserCheckpointRepository(),
                authentication_profiles=(
                    authentication_profiles
                    or InMemoryAuthenticationProfileRepository()
                ),
            ),
        )
    )


def test_backend_serves_a_session_lifecycle() -> None:
    state = FakeBrowserRuntime()
    app = create_test_app(
        FakeProvisioner(),
        InMemoryBrowserRepository(),
        InMemorySessionRepository(),
        state,
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200

        created = client.post(
            "/api/v1/sessions",
            json={"owner_id": OWNER_ID},
        )
        assert created.status_code == 201
        session = created.json()
        assert session["remaining_capacity"] == 0
        browser_state = client.get(f"/api/v1/sessions/{session['id']}/browser-state")
        assert browser_state.status_code == 200
        assert browser_state.json()["tabs"][0]["url"].endswith("/inbox")
        downloads = client.get(f"/api/v1/sessions/{session['id']}/downloads")
        assert downloads.status_code == 200
        assert downloads.headers["cache-control"] == "no-store"
        assert downloads.json() == []
        assert session["browser_id"] == str(UUID(int=1))
        assert session["tunnel_path"] == f"/api/v1/sessions/{session['id']}/tunnel"

        # The only browser is now leased, so a second session has to wait.
        exhausted = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID})
        assert exhausted.status_code == 503
        assert exhausted.json()["code"] == "no_browser_available"

        assert client.get(f"/api/v1/sessions/{session['id']}").status_code == 200
        assert client.delete(f"/api/v1/sessions/{session['id']}").status_code == 204

        closed = client.get(f"/api/v1/sessions/{session['id']}")
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"

        # Releasing the lease returned the browser to the pool.
        reopened = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID})
        assert reopened.status_code == 201


def test_admin_sees_the_pool_and_can_pull_a_browser_out_of_it() -> None:
    provisioner = FakeProvisioner()
    app = create_test_app(
        provisioner,
        InMemoryBrowserRepository(),
        InMemorySessionRepository(),
        FakeBrowserRuntime(),
    )
    with TestClient(app) as client:
        session = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID}).json()

        browsers = client.get("/api/v1/admin/browsers")
        assert browsers.status_code == 200
        assert browsers.json()[0]["state"] == "leased"
        assert browsers.json()[0]["lease"]["session_id"] == session["id"]

        sessions = client.get("/api/v1/admin/sessions")
        assert sessions.status_code == 200
        assert [entry["id"] for entry in sessions.json()] == [session["id"]]

        released = client.post(
            f"/api/v1/admin/browsers/{session['browser_id']}/release"
        )
        assert released.status_code == 200
        assert released.json()["state"] == "stopped"
        assert provisioner.released == [UUID(int=1)]
        # The aggregate remains available as history after its browser is gone.
        closed_sessions = client.get("/api/v1/admin/sessions").json()
        assert [entry["status"] for entry in closed_sessions] == ["closed"]

        restarted = client.post(
            f"/api/v1/admin/browsers/{session['browser_id']}/restart"
        )
        assert restarted.status_code == 200
        assert restarted.json()["state"] == "ready"
        assert provisioner.started == [UUID(int=1)]
        assert (
            client.post("/api/v1/sessions", json={"owner_id": OWNER_ID}).status_code
            == 201
        )

        unknown = client.post(f"/api/v1/admin/browsers/{UUID(int=99)}/release")
        assert unknown.status_code == 404
        assert unknown.json()["code"] == "browser_not_found"


def test_a_suspended_session_frees_its_browser_and_comes_back() -> None:
    state = FakeBrowserRuntime()
    app = create_test_app(
        FakeProvisioner(),
        InMemoryBrowserRepository(),
        InMemorySessionRepository(),
        state,
    )
    with TestClient(app) as client:
        opened = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID}).json()

        suspended = client.post(f"/api/v1/sessions/{opened['id']}/suspend")
        assert suspended.status_code == 200
        assert suspended.json()["status"] == "suspended"
        assert suspended.json()["browser_id"] is None

        # The browser went back to the pool while the session lives on.
        other = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID})
        assert other.status_code == 201
        client.delete(f"/api/v1/sessions/{other.json()['id']}")

        resumed = client.post(f"/api/v1/sessions/{opened['id']}/resume", json={})
        assert resumed.status_code == 200
        assert resumed.json()["status"] == "active"
        # The session kept its id, so the links handed out before still work.
        assert resumed.json()["id"] == opened["id"]
        assert state.mounted_authentication == {"cookies": [], "localStorage": []}
        assert state.mounted_browser is not None
        assert state.mounted_browser["tabs"][0]["url"] == "https://example.com/inbox"


def test_saved_browser_and_authentication_states_are_independent() -> None:
    app = create_test_app(
        FakeProvisioner(),
        InMemoryBrowserRepository(),
        InMemorySessionRepository(),
        FakeBrowserRuntime(),
        InMemoryBrowserCheckpointRepository(),
        InMemoryAuthenticationProfileRepository(),
    )
    with TestClient(app) as client:
        session = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID}).json()
        browser = client.post(
            f"/api/v1/sessions/{session['id']}/browser-checkpoints",
            json={},
        )
        authentication = client.post(
            f"/api/v1/sessions/{session['id']}/authentication-profiles",
            json={"name": "Work"},
        )

        assert browser.status_code == authentication.status_code == 201
        assert "browser_state" not in browser.json()
        assert "authentication_state" not in authentication.json()
        assert len(client.get("/api/v1/browser-checkpoints").json()) == 1
        auth_list = client.get("/api/v1/authentication-profiles")
        assert auth_list.headers["cache-control"] == "no-store"
        assert len(auth_list.json()) == 1

        profile_id = authentication.json()["id"]
        updated = client.put(
            f"/api/v1/sessions/{session['id']}/authentication-profiles/{profile_id}",
            json={"name": "Work updated"},
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Work updated"
        assert "authentication_state" not in updated.json()
        mounted = client.put(
            f"/api/v1/sessions/{session['id']}/authentication-profile",
            json={"authentication_profile_id": profile_id},
        )
        assert mounted.status_code == 204
        deleted = client.delete(f"/api/v1/authentication-profiles/{profile_id}")
        assert deleted.status_code == 204


def test_a_client_finds_its_own_sessions_again() -> None:
    """A reloaded page asks the backend what it owns instead of remembering."""
    app = create_test_app(
        FakeProvisioner(),
        InMemoryBrowserRepository(),
        InMemorySessionRepository(),
        FakeBrowserRuntime(),
    )
    with TestClient(app) as client:
        session = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID}).json()

        owned = client.get("/api/v1/sessions", params={"owner_id": OWNER_ID})
        assert owned.status_code == 200
        assert [entry["id"] for entry in owned.json()["sessions"]] == [session["id"]]
        assert owned.json()["sessions"][0]["tunnel_path"] is not None
        # The only browser is taken, so the page must not offer another one.
        assert owned.json()["remaining_capacity"] == 0

        # A session belongs to the client that opened it, not to everyone.
        stranger = client.get("/api/v1/sessions", params={"owner_id": str(UUID(int=8))})
        assert stranger.json()["sessions"] == []
        assert stranger.json()["remaining_capacity"] == 0

        # A parked session is still the client's, and its browser is free again.
        client.post(f"/api/v1/sessions/{session['id']}/suspend")
        parked = client.get("/api/v1/sessions", params={"owner_id": OWNER_ID})
        assert [entry["status"] for entry in parked.json()["sessions"]] == ["suspended"]
        assert parked.json()["remaining_capacity"] == 1
