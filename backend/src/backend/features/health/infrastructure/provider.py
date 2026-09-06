from dishka import Provider, Scope, provide

from backend.features.browsers.application.ports import BrowserRepository
from backend.features.health.application.service import HealthService
from backend.lifecycle import Lifecycle


class HealthProvider(Provider):
    @provide(scope=Scope.APP)
    def lifecycle(self) -> Lifecycle:
        return Lifecycle()

    @provide(scope=Scope.REQUEST)
    def health_service(
        self,
        lifecycle: Lifecycle,
        browsers: BrowserRepository,
    ) -> HealthService:
        return HealthService(lifecycle, browsers.list)
