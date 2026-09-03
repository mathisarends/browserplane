from dishka import Provider, Scope, provide

from data_plane.features.health.application.service import HealthService


class HealthProvider(Provider):
    @provide(scope=Scope.APP)
    def health_service(self) -> HealthService:
        return HealthService()
