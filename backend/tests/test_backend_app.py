from fastapi.testclient import TestClient

from backend.app import create_app


def test_backend_serves_a_session_lifecycle() -> None:
    owner_id = "11111111-1111-1111-1111-111111111111"
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200

        created = client.post("/api/v1/sessions", json={"owner_id": owner_id})
        assert created.status_code == 201
        session = created.json()
        assert session["tunnel_path"] == f"/api/v1/sessions/{session['id']}/tunnel"

        assert client.get(f"/api/v1/sessions/{session['id']}").status_code == 200
        assert client.delete(f"/api/v1/sessions/{session['id']}").status_code == 204

        missing = client.get(f"/api/v1/sessions/{session['id']}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "session_not_found"
