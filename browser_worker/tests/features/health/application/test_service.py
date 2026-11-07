from pathlib import Path

from tests.fakes import FakeBrowserProcess

from browser_worker.features.health.application import HealthService, HealthStatus
from browser_worker.features.workspace.infrastructure.filesystem import (
    FilesystemWorkspace,
)


def test_readiness_checks_worker_capabilities(tmp_path: Path) -> None:
    browser = FakeBrowserProcess()
    service = HealthService(FilesystemWorkspace(tmp_path), browser)

    assert service.liveness() is HealthStatus.OK
    assert service.readiness() is HealthStatus.OK

    browser.available = False
    assert service.readiness() is HealthStatus.NOT_READY
