from collections.abc import Callable
from pathlib import Path

import pytest
from tests.fakes import FakeBrowserProcess

from browser_worker.features.health.application.service import HealthService
from browser_worker.features.release.application.exceptions import (
    WorkerNotSupervisedException,
)
from browser_worker.features.release.application.restart import WorkerRestartService
from browser_worker.features.release.application.settings import RestartSettings
from browser_worker.features.workspace.application.workspace import Workspace


class RecordedRestartService(WorkerRestartService):
    """Restart service whose process-ending timers are recorded, not started."""

    def __init__(self, health: HealthService, settings: RestartSettings) -> None:
        super().__init__(health, settings)
        self.scheduled: list[Callable[[], None]] = []

    def _later(self, delay: float, action: Callable[[], None]) -> None:
        self.scheduled.append(action)


def _health(tmp_path: Path) -> HealthService:
    return HealthService(Workspace(tmp_path), FakeBrowserProcess())


def test_an_unsupervised_worker_keeps_running(tmp_path: Path) -> None:
    service = RecordedRestartService(
        _health(tmp_path), RestartSettings(supervised=False)
    )

    with pytest.raises(WorkerNotSupervisedException):
        service.restart()
    assert service.scheduled == []


def test_a_supervised_worker_names_the_instance_it_retires(tmp_path: Path) -> None:
    health = _health(tmp_path)
    service = RecordedRestartService(health, RestartSettings(supervised=True))

    retiring = service.restart()

    assert retiring == health.instance_id
    assert len(service.scheduled) == 1
