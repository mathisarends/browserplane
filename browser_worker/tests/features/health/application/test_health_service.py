from pathlib import Path

from tests.fakes import FakeBrowserProcess

from browser_worker.features.health.application.models import HealthStatus
from browser_worker.features.health.application.service import HealthService
from browser_worker.features.workspace.application.workspace import Workspace


def test_readiness_checks_worker_capabilities(tmp_path: Path) -> None:
    browser = FakeBrowserProcess()
    service = HealthService(Workspace(tmp_path), browser)

    assert service.liveness().status is HealthStatus.OK
    assert service.readiness().status is HealthStatus.OK

    browser.available = False
    assert service.readiness().status is HealthStatus.NOT_READY
