from fastapi.testclient import TestClient

from control_plane.app import create_app


def test_lists_two_browser_data_planes() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/browsers")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "browser-1",
            "status": "ready",
            "websocket_url": "/api/browsers/browser-1/ws",
        },
        {
            "id": "browser-2",
            "status": "ready",
            "websocket_url": "/api/browsers/browser-2/ws",
        },
    ]
