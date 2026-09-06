from dishka import Provider, Scope, provide

from browser_worker.features.release.application.service import WorkerReleaseService


class ReleaseProvider(Provider):
    release_service = provide(WorkerReleaseService, scope=Scope.APP)
