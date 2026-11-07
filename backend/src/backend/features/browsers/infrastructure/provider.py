from dishka import Provider, Scope, provide

from backend.features.browsers.application import BrowserService, BrowserWorkerRoutes
from backend.features.browsers.domain import (
    BrowserProvisioner,
    BrowserRepository,
    BrowserWorkerDirectory,
    WorkerRecovery,
)
from backend.features.browsers.infrastructure.browser_worker_provisioner import (
    BrowserWorkerProvisioner,
)
from backend.features.browsers.infrastructure.repository import SqlBrowserRepository
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.features.browsers.infrastructure.static_directory import (
    StaticBrowserWorkerDirectory,
)
from backend.features.browsers.infrastructure.supervised_worker_recovery import (
    SupervisedWorkerRecovery,
)


class BrowserProvider(Provider):
    routes = provide(BrowserWorkerRoutes, scope=Scope.APP, provides=BrowserWorkerRoutes)

    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> BrowserPoolSettings:
        return BrowserPoolSettings()

    directory = provide(
        StaticBrowserWorkerDirectory, scope=Scope.APP, provides=BrowserWorkerDirectory
    )

    provisioner = provide(
        BrowserWorkerProvisioner, scope=Scope.APP, provides=BrowserProvisioner
    )

    recovery = provide(
        SupervisedWorkerRecovery, scope=Scope.APP, provides=WorkerRecovery
    )

    repository = provide(
        SqlBrowserRepository, scope=Scope.REQUEST, provides=BrowserRepository
    )

    browser_service = provide(
        BrowserService, scope=Scope.REQUEST, provides=BrowserService
    )
