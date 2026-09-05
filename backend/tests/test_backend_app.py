from uuid import UUID

from fastapi.testclient import TestClient

from backend.app import create_app
from backend.features.browsers.application.models import BrowserSlot
from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.infrastructure.in_memory_repository import (
    InMemoryBrowserRepository,
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


def test_backend_serves_a_session_lifecycle() -> None:
    app = create_app(FakeProvisioner(), InMemoryBrowserRepository())
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
