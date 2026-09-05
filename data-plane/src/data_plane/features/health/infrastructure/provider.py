from dishka import Provider, Scope, provide

from data_plane.features.browser.infrastructure import ChromeProcess
from data_plane.features.browser.infrastructure.settings import BrowserSettings
from data_plane.features.health.application.service import HealthService
from data_plane.features.workspace.application.workspace import Workspace
from data_plane.lifecycle import Lifecycle


class HealthProvider(Provider):
    @provide(scope=Scope.APP)
    def lifecycle(self) -> Lifecycle:
        return Lifecycle()

    @provide(scope=Scope.APP)
    def health_service(
        self,
        lifecycle: Lifecycle,
        workspace: Workspace,
        settings: BrowserSettings,
    ) -> HealthService:
        return HealthService(
            lifecycle,
            workspace.is_available,
            lambda: ChromeProcess.is_available(settings),
        )
