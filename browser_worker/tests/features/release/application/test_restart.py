from pathlib import Path

import pytest
from tests.fakes import FakeBrowserProcess

from browser_worker.features.health.application import HealthService
from browser_worker.features.release.application import (
    RestartSettings,
    WorkerNotSupervisedException,
    WorkerRestarter,
    WorkerRestartService,
)
from browser_worker.features.workspace.infrastructure.filesystem import (
    FilesystemWorkspace,
)


class FakeWorkerRestarter(WorkerRestarter):
    def __init__(self) -> None:
        self.scheduled: list[tuple[float, float]] = []

    def schedule(self, response_delay: float, shutdown_timeout: float) -> None:
        self.scheduled.append((response_delay, shutdown_timeout))


def _health(tmp_path: Path) -> HealthService:
    return HealthService(FilesystemWorkspace(tmp_path), FakeBrowserProcess())


def test_an_unsupervised_worker_keeps_running(tmp_path: Path) -> None:
    restarter = FakeWorkerRestarter()
    service = WorkerRestartService(
        _health(tmp_path), RestartSettings(supervised=False), restarter
    )

    with pytest.raises(WorkerNotSupervisedException):
        service.restart()
    assert restarter.scheduled == []


def test_a_supervised_worker_names_the_instance_it_retires(tmp_path: Path) -> None:
    health = _health(tmp_path)
    restarter = FakeWorkerRestarter()
    service = WorkerRestartService(health, RestartSettings(supervised=True), restarter)

    retiring = service.restart()

    assert retiring == health.instance_id
    assert len(restarter.scheduled) == 1
