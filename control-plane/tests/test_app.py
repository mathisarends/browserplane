from uuid import UUID

from fastapi.testclient import TestClient

from control_plane.app import create_app
from control_plane.features.browsers.application.models import BrowserSlot
from control_plane.features.browsers.application.ports import BrowserProvisioner


class FakeProvisioner(BrowserProvisioner):
    async def provision(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot(
                UUID(int=1),
                "http://worker-1",
                "ws://tunnel-1/ws",
                "ws://worker-1/screencast",
            ),
            BrowserSlot(
                UUID(int=2),
                "http://worker-2",
                "ws://tunnel-2/ws",
                "ws://worker-2/screencast",
            ),
        )

    async def deprovision(self) -> None:
        pass


def test_lists_two_browser_data_planes() -> None:
    with TestClient(create_app(FakeProvisioner())) as client:
        response = client.get("/api/v1/browsers")

    assert response.status_code == 200
    assert [browser["id"] for browser in response.json()] == [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    ]
    assert [browser["websocket_url"] for browser in response.json()] == [
        "ws://tunnel-1/ws",
        "ws://tunnel-2/ws",
    ]
    assert [browser["screencast_url"] for browser in response.json()] == [
        "ws://worker-1/screencast",
        "ws://worker-2/screencast",
    ]


def test_unknown_browser_returns_api_error() -> None:
    with TestClient(create_app(FakeProvisioner())) as client:
        response = client.get(f"/api/v1/browsers/{UUID(int=9)}")

    assert response.status_code == 404
    assert response.json() == {
        "code": "browser_not_found",
        "message": "Browser not found",
    }
