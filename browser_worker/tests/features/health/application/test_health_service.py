from browser_worker.features.health.application.models import HealthStatus
from browser_worker.features.health.application.service import HealthService


def test_readiness_checks_worker_capabilities() -> None:
    browser_available = True
    service = HealthService(
        lambda: True,
        lambda: browser_available,
    )

    assert service.liveness().status is HealthStatus.OK
    assert service.readiness().status is HealthStatus.OK

    browser_available = False
    assert service.readiness().status is HealthStatus.NOT_READY
