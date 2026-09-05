from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)
from backend.features.browsers.application.service import BrowserService
from backend.features.browsers.infrastructure.data_plane_provisioner import (
    DataPlaneBrowserProvisioner,
)
from backend.features.browsers.infrastructure.repository import SqlBrowserRepository
from backend.settings import BackendSettings


class BrowserProvider(Provider):
    def __init__(
        self,
        provisioner: BrowserProvisioner | None = None,
        repository: BrowserRepository | None = None,
    ) -> None:
        super().__init__()
        self._provisioner = provisioner
        self._repository = repository

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(self, settings: BackendSettings) -> BrowserProvisioner:
        return self._provisioner or DataPlaneBrowserProvisioner(settings)

    @provide(scope=Scope.REQUEST, provides=BrowserRepository)
    def repository(self, session: AsyncSession) -> BrowserRepository:
        return self._repository or SqlBrowserRepository(session)

    @provide(scope=Scope.REQUEST)
    def browser_service(
        self, provisioner: BrowserProvisioner, repository: BrowserRepository
    ) -> BrowserService:
        return BrowserService(provisioner, repository)
