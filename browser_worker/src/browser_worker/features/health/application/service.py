from uuid import UUID, uuid4

from browser_worker.features.browser.application.ports import BrowserProcess
from browser_worker.features.health.application.models import HealthStatus
from browser_worker.features.workspace.application.workspace import Workspace


class HealthService:
    def __init__(self, workspace: Workspace, browser: BrowserProcess) -> None:
        self._workspace = workspace
        self._browser = browser
        self._instance_id = uuid4()

    @property
    def instance_id(self) -> UUID:
        return self._instance_id

    def liveness(self) -> HealthStatus:
        """Report that the worker process itself is running."""
        return HealthStatus.OK

    def readiness(self) -> HealthStatus:
        """Report whether the worker can actually run a browser session."""
        if not self._workspace.is_available() or not self._browser.is_available():
            return HealthStatus.NOT_READY
        return HealthStatus.OK
