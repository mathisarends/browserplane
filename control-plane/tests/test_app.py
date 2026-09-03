from uuid import UUID

from fastapi.testclient import TestClient

from control_plane.app import create_app
from control_plane.settings import BrowserSlot


class FakeProvisioner:
    async def provision(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot(UUID(int=1), "http://worker-1", "ws://tunnel-1/ws"),
            BrowserSlot(UUID(int=2), "http://worker-2", "ws://tunnel-2/ws"),
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
