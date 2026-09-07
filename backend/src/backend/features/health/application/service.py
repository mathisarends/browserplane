from collections.abc import Awaitable, Callable

from backend.features.health.application.models import Health, HealthStatus


class HealthService:
    def __init__(self, check_persistence: Callable[[], Awaitable[None]]) -> None:
        self._check_persistence = check_persistence

    def liveness(self) -> Health:
        """Answering at all is the check; never fail on a downstream dependency."""
        return Health(status=HealthStatus.OK)

    async def readiness(self) -> Health:
        try:
            await self._check_persistence()
        except Exception:
            return Health(status=HealthStatus.NOT_READY)
        return Health(status=HealthStatus.OK)
