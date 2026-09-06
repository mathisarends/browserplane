from dishka import Provider, Scope, provide
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)
from backend.features.browsers.application.service import BrowserService
from backend.features.browsers.infrastructure.browser_worker_provisioner import (
    BrowserWorkerProvisioner,
)
from backend.features.browsers.infrastructure.repository import SqlBrowserRepository
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings


class BrowserProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> BrowserPoolSettings:
        return BrowserPoolSettings()

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(
        self,
        settings: BrowserPoolSettings,
        http: AsyncClient,
        worker_settings: BrowserWorkerSettings,
    ) -> BrowserProvisioner:
        return BrowserWorkerProvisioner(settings, http, worker_settings)

    @provide(scope=Scope.REQUEST, provides=BrowserRepository)
    def repository(self, session: AsyncSession) -> BrowserRepository:
        return SqlBrowserRepository(session)

    @provide(scope=Scope.REQUEST)
    def browser_service(
        self, provisioner: BrowserProvisioner, repository: BrowserRepository
    ) -> BrowserService:
        return BrowserService(provisioner, repository)
