import logging
import os
import signal
import threading
from collections.abc import Callable

from browser_worker.features.release.application import WorkerRestarter

logger = logging.getLogger(__name__)


class ProcessRestarter(WorkerRestarter):
    def __init__(self) -> None:
        self._shutdown_timeout = 15.0

    def schedule(self, response_delay: float, shutdown_timeout: float) -> None:
        self._shutdown_timeout = shutdown_timeout
        self._later(response_delay, self._terminate)

    def _terminate(self) -> None:
        # SIGTERM unwinds the lifespan, which stops Chromium and closes the
        # container. The hard exit is the fence for a shutdown that hangs on
        # exactly the state this restart is shedding.
        self._later(self._shutdown_timeout, self._abort)
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
