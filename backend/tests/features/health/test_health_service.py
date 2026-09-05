import asyncio

from backend.features.health.application.models import HealthStatus
from backend.features.health.application.service import HealthService
from backend.lifecycle import Lifecycle


def test_readiness_tracks_lifecycle_and_persistence() -> None:
    lifecycle = Lifecycle()
    persistence_available = True

    async def check_persistence() -> None:
        if not persistence_available:
            raise ConnectionError

    service = HealthService(lifecycle, check_persistence)

    assert service.liveness().status is HealthStatus.OK
    assert asyncio.run(service.readiness()).status is HealthStatus.NOT_READY

    lifecycle.mark_ready()
    assert asyncio.run(service.readiness()).status is HealthStatus.OK

    persistence_available = False
    assert asyncio.run(service.readiness()).status is HealthStatus.NOT_READY

    persistence_available = True
    lifecycle.start_draining()
    assert asyncio.run(service.readiness()).status is HealthStatus.NOT_READY
