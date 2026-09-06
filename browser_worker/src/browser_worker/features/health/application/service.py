from browser_worker.features.browser.application.ports import BrowserProcess
from browser_worker.features.health.application.models import Health, HealthStatus
from browser_worker.features.workspace.application.workspace import Workspace


class HealthService:
    def __init__(self, workspace: Workspace, browser: BrowserProcess) -> None:
        self._workspace = workspace
        self._browser = browser

    def liveness(self) -> Health:
        return Health(status=HealthStatus.OK)

    def readiness(self) -> Health:
        if not self._workspace.is_available() or not self._browser.is_available():
            return Health(status=HealthStatus.NOT_READY)
        return Health(status=HealthStatus.OK)
