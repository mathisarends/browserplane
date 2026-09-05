from dishka import Provider, Scope, provide

from browser_worker.features.browser.infrastructure import ChromeProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings
from browser_worker.features.health.application.service import HealthService
from browser_worker.features.workspace.application.workspace import Workspace
from browser_worker.lifecycle import Lifecycle


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
