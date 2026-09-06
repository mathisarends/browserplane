from dishka import Provider, Scope, provide

from browser_worker.features.release.application.service import WorkerReleaseService
from browser_worker.features.release.application.settings import ReleaseSettings


class ReleaseProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ReleaseSettings:
        return ReleaseSettings()

    release_service = provide(WorkerReleaseService, scope=Scope.APP)
