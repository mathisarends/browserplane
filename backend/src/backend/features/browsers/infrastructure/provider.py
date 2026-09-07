from dishka import Provider, Scope, provide
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
    BrowserWorkerDirectory,
    WorkerRecovery,
)
from backend.features.browsers.application.service import BrowserService
from backend.features.browsers.infrastructure.browser_worker_provisioner import (
    BrowserWorkerProvisioner,
)
from backend.features.browsers.infrastructure.repository import SqlBrowserRepository
from backend.features.browsers.infrastructure.routes import BrowserWorkerRoutes
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.features.browsers.infrastructure.static_directory import (
    StaticBrowserWorkerDirectory,
)
from backend.features.browsers.infrastructure.supervised_worker_recovery import (
    SupervisedWorkerRecovery,
)
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings


class BrowserProvider(Provider):
    @provide(scope=Scope.APP)
    def routes(self) -> BrowserWorkerRoutes:
        return BrowserWorkerRoutes()

    @provide(scope=Scope.APP)
    def settings(self) -> BrowserPoolSettings:
        return BrowserPoolSettings()

    @provide(scope=Scope.APP, provides=BrowserWorkerDirectory)
    def directory(self, settings: BrowserPoolSettings) -> BrowserWorkerDirectory:
        return StaticBrowserWorkerDirectory(settings)

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(
        self,
        directory: BrowserWorkerDirectory,
        http: AsyncClient,
        worker_settings: BrowserWorkerSettings,
    ) -> BrowserProvisioner:
        return BrowserWorkerProvisioner(directory, http, worker_settings)

    @provide(scope=Scope.APP, provides=WorkerRecovery)
    def recovery(
        self, http: AsyncClient, worker_settings: BrowserWorkerSettings
    ) -> WorkerRecovery:
        return SupervisedWorkerRecovery(http, worker_settings)

    @provide(scope=Scope.REQUEST, provides=BrowserRepository)
    def repository(self, session: AsyncSession) -> BrowserRepository:
        return SqlBrowserRepository(session)

    @provide(scope=Scope.REQUEST)
    def browser_service(
        self,
        provisioner: BrowserProvisioner,
        repository: BrowserRepository,
        recovery: WorkerRecovery,
    ) -> BrowserService:
        return BrowserService(provisioner, repository, recovery)
