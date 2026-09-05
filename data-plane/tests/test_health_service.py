from data_plane.features.health.application.models import HealthStatus
from data_plane.features.health.application.service import HealthService
from data_plane.lifecycle import Lifecycle


def test_readiness_checks_worker_capabilities() -> None:
    lifecycle = Lifecycle()
    browser_available = True
    service = HealthService(
        lifecycle,
        lambda: True,
        lambda: browser_available,
    )

    assert service.liveness().status is HealthStatus.OK
    assert service.readiness().status is HealthStatus.OK

    browser_available = False
    assert service.readiness().status is HealthStatus.NOT_READY

    browser_available = True
    lifecycle.start_draining()
    assert service.readiness().status is HealthStatus.NOT_READY
