from data_plane.features.health.application.models import Health, HealthStatus


class HealthService:
    """Answer whether the worker is alive and ready to accept browsers."""

    def liveness(self) -> Health:
        return Health(status=HealthStatus.OK)

    def readiness(self) -> Health:
        return Health(status=HealthStatus.OK)
