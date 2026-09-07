from dishka import Provider, Scope, provide

from browser_worker.features.release.application.restart import WorkerRestartService
from browser_worker.features.release.application.service import WorkerReleaseService
from browser_worker.features.release.application.settings import (
    ReleaseSettings,
    RestartSettings,
)


class ReleaseProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ReleaseSettings:
        return ReleaseSettings()

    @provide(scope=Scope.APP)
    def restart_settings(self) -> RestartSettings:
        return RestartSettings()

    release_service = provide(WorkerReleaseService, scope=Scope.APP)
    restart_service = provide(WorkerRestartService, scope=Scope.APP)
