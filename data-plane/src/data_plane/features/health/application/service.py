from collections.abc import Callable

from data_plane.features.health.application.models import Health, HealthStatus
from data_plane.lifecycle import Lifecycle


class HealthService:
    def __init__(
        self,
        lifecycle: Lifecycle,
        workspace_is_available: Callable[[], bool],
        browser_is_available: Callable[[], bool],
    ) -> None:
        self._lifecycle = lifecycle
        self._workspace_is_available = workspace_is_available
        self._browser_is_available = browser_is_available

    def liveness(self) -> Health:
        return Health(status=HealthStatus.OK)

    def readiness(self) -> Health:
        if (
            self._lifecycle.is_draining
            or not self._workspace_is_available()
            or not self._browser_is_available()
        ):
            return Health(status=HealthStatus.NOT_READY)
        return Health(status=HealthStatus.OK)
