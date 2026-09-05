from uuid import UUID

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.features.browsers.application.models import Browser, BrowserSlot
from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.infrastructure.in_memory_repository import (
    InMemoryBrowserRepository,
)
from backend.features.sessions.application.models import BrowserStateDocument
from backend.features.sessions.application.ports import BrowserStateGateway
from backend.features.sessions.infrastructure.in_memory_repository import (
    InMemorySuspendedSessionRepository,
)

OWNER_ID = str(UUID(int=7))


class FakeProvisioner(BrowserProvisioner):
    async def provision(self) -> tuple[BrowserSlot, ...]:
        return (
            BrowserSlot(
                UUID(int=1),
                "http://worker-1",
                "ws://tunnel-1/ws",
                "ws://worker-1/screencast",
            ),
        )

    async def deprovision(self) -> None:
        pass


class FakeBrowserStateGateway(BrowserStateGateway):
    """Keep the captured document, the way a worker would hand it back."""

    def __init__(self) -> None:
        self.mounted: BrowserStateDocument | None = None

    async def capture(self, browser: Browser) -> BrowserStateDocument:
        return {
            "tabs": [{"url": "https://example.com/inbox"}],
            "active_tab_index": 0,
            "authentication": {"cookies": [], "origins": []},
        }

    async def mount(self, browser: Browser, state: BrowserStateDocument) -> None:
        self.mounted = state


def test_backend_serves_a_session_lifecycle() -> None:
    app = create_app(
        FakeProvisioner(),
        InMemoryBrowserRepository(),
        InMemorySuspendedSessionRepository(),
        FakeBrowserStateGateway(),
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200

        created = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID})
        assert created.status_code == 201
        session = created.json()
        assert session["browser_id"] == str(UUID(int=1))
        assert session["tunnel_path"] == f"/api/v1/sessions/{session['id']}/tunnel"

        # The only browser is now leased, so a second session has to wait.
        exhausted = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID})
        assert exhausted.status_code == 503
        assert exhausted.json()["code"] == "no_browser_available"

        assert client.get(f"/api/v1/sessions/{session['id']}").status_code == 200
        assert client.delete(f"/api/v1/sessions/{session['id']}").status_code == 204

        missing = client.get(f"/api/v1/sessions/{session['id']}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "session_not_found"

        # Releasing the lease returned the browser to the pool.
        reopened = client.post("/api/v1/sessions", json={"owner_id": OWNER_ID})
        assert reopened.status_code == 201


def test_a_suspended_session_frees_its_browser_and_comes_back() -> None:
    state = FakeBrowserStateGateway()
    app = create_app(
        FakeProvisioner(),
        InMemoryBrowserRepository(),
        InMemorySuspendedSessionRepository(),
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
        assert state.mounted is not None
        assert state.mounted["tabs"][0]["url"] == "https://example.com/inbox"
