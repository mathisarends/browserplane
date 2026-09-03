from fastapi.testclient import TestClient

from control_plane.app import create_app
from control_plane.settings import BrowserSlot


class FakeProvisioner:
    async def provision(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot("browser-1", "http://worker-1", "ws://tunnel-1/ws"),
            BrowserSlot("browser-2", "http://worker-2", "ws://tunnel-2/ws"),
        )

    async def deprovision(self) -> None:
        pass


def test_lists_two_browser_data_planes() -> None:
    with TestClient(create_app(FakeProvisioner())) as client:
        response = client.get("/api/v1/browsers")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "browser-1",
            "status": "ready",
            "websocket_url": "/api/v1/browsers/browser-1/ws",
        },
        {
            "id": "browser-2",
            "status": "ready",
            "websocket_url": "/api/v1/browsers/browser-2/ws",
        },
    ]
