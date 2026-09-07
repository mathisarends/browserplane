import asyncio

from backend.features.health.application.models import HealthStatus
from backend.features.health.application.service import HealthService


def test_readiness_tracks_persistence() -> None:
    persistence_available = True

    async def check_persistence() -> None:
        if not persistence_available:
            raise ConnectionError

    service = HealthService(check_persistence)

    assert service.liveness().status is HealthStatus.OK
    assert asyncio.run(service.readiness()).status is HealthStatus.OK

    persistence_available = False
    assert asyncio.run(service.readiness()).status is HealthStatus.NOT_READY


def test_liveness_ignores_persistence() -> None:
    async def check_persistence() -> None:
        raise ConnectionError

    assert HealthService(check_persistence).liveness().status is HealthStatus.OK
