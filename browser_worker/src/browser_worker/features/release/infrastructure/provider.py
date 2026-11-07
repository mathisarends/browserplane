from dishka import Provider, Scope, provide

from browser_worker.features.release.application import (
    ReleaseSettings,
    RestartSettings,
    WorkerReleaseService,
    WorkerRestarter,
    WorkerRestartService,
)
from browser_worker.features.release.infrastructure.process import ProcessRestarter
from browser_worker.features.release.infrastructure.settings import (
    EnvironmentReleaseSettings,
    EnvironmentRestartSettings,
)


class ReleaseProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> ReleaseSettings:
        return EnvironmentReleaseSettings()

    @provide(scope=Scope.APP)
    def restart_settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> RestartSettings:
        return EnvironmentRestartSettings()

    restarter = provide(ProcessRestarter, scope=Scope.APP, provides=WorkerRestarter)

    release_service = provide(WorkerReleaseService, scope=Scope.APP)
    restart_service = provide(WorkerRestartService, scope=Scope.APP)
