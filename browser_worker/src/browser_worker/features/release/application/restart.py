import logging
from uuid import UUID

from browser_worker.features.health.application import HealthService
from browser_worker.features.release.application.exceptions import (
    WorkerNotSupervisedException,
)
from browser_worker.features.release.application.ports import WorkerRestarter
from browser_worker.features.release.application.settings import RestartSettings

logger = logging.getLogger(__name__)


class WorkerRestartService:
    """Trade this worker process for a fresh one from its supervisor.

    Replacing the whole worker is the last escalation of a release that cannot
    clean itself: with the process go the browser runtime, its child processes
    and every in-memory handle a retry can no longer reach.
    """

    def __init__(
        self,
        health: HealthService,
        settings: RestartSettings,
        restarter: WorkerRestarter,
    ) -> None:
        self._health = health
        self._settings = settings
        self._restarter = restarter

    def restart(self) -> UUID:
        """Retire this instance and name the id the caller must stop seeing."""
        if not self._settings.supervised:
            raise WorkerNotSupervisedException
        retiring = self._health.instance_id
        logger.warning("Worker restart requested instance_id=%s", retiring)
        # Late enough for this response to reach the control plane, which needs
        # the retiring id to tell the replacement from the process it replaced.
        self._restarter.schedule(
            self._settings.response_delay, self._settings.shutdown_timeout
        )
        return retiring
