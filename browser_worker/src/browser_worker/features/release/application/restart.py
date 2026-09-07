import logging
import os
import signal
import threading
from collections.abc import Callable
from uuid import UUID

from browser_worker.features.health.application.service import HealthService
from browser_worker.features.release.application.exceptions import (
    WorkerNotSupervisedException,
)
from browser_worker.features.release.application.settings import RestartSettings

logger = logging.getLogger(__name__)


class WorkerRestartService:
    """Trade this worker process for a fresh one from its supervisor.

    Replacing the whole worker is the last escalation of a release that cannot
    clean itself: with the process go the browser runtime, its child processes
    and every in-memory handle a retry can no longer reach.
    """

    def __init__(self, health: HealthService, settings: RestartSettings) -> None:
        self._health = health
        self._settings = settings

    def restart(self) -> UUID:
        """Retire this instance and name the id the caller must stop seeing."""
        if not self._settings.supervised:
            raise WorkerNotSupervisedException
        retiring = self._health.instance_id
        logger.warning("Worker restart requested instance_id=%s", retiring)
        # Late enough for this response to reach the control plane, which needs
        # the retiring id to tell the replacement from the process it replaced.
        self._later(self._settings.response_delay, self._terminate)
        return retiring

    def _terminate(self) -> None:
        # SIGTERM unwinds the lifespan, which stops Chromium and closes the
        # container. The hard exit is the fence for a shutdown that hangs on
        # exactly the state this restart is shedding.
        self._later(self._settings.shutdown_timeout, self._abort)
        signal.raise_signal(signal.SIGTERM)

    def _abort(self) -> None:
        logger.error("Worker shutdown timed out; ending the process")
        os._exit(1)

    def _later(self, delay: float, action: Callable[[], None]) -> None:
        # A daemon timer, not the event loop: the loop is part of what may be
        # wedged, and a lingering timer must never hold the process open.
        timer = threading.Timer(delay, action)
        timer.daemon = True
        timer.start()
