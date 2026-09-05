from collections.abc import Awaitable, Callable

from backend.features.health.application.models import Health, HealthStatus
from backend.lifecycle import Lifecycle


class HealthService:
    def __init__(
        self,
        lifecycle: Lifecycle,
        check_persistence: Callable[[], Awaitable[object]],
    ) -> None:
        self._lifecycle = lifecycle
        self._check_persistence = check_persistence

    def liveness(self) -> Health:
        return Health(status=HealthStatus.OK)

    async def readiness(self) -> Health:
        if not self._lifecycle.is_ready:
            return Health(status=HealthStatus.NOT_READY)
        try:
            await self._check_persistence()
        except Exception:
            return Health(status=HealthStatus.NOT_READY)
        return Health(status=HealthStatus.OK)
