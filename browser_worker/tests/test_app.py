from fastapi.testclient import TestClient
from tests.fakes import FakeBrowserProcess

from browser_worker.app import create_app
from browser_worker.features.browser.application.service import BrowserService


def test_worker_exposes_health_and_readiness() -> None:
    process = FakeBrowserProcess()

    with TestClient(create_app(BrowserService(process))) as client:
        health = client.get("/api/v1/health")
        readiness = client.get("/api/v1/readiness")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert readiness.status_code == 200
    assert readiness.json()["status"] in {"ok", "not_ready"}
    assert process.stop_count == 0


def test_openapi_identifies_the_browser_worker() -> None:
    document = create_app().openapi()

    assert document["info"]["title"] == "Browser Worker"
