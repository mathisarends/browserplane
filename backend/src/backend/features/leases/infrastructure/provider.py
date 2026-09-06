from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.ports import BrowserAllocator, LeaseStore
from backend.features.leases.application.service import LeaseService
from backend.features.leases.infrastructure.browser_service_allocator import (
    BrowserServiceAllocator,
)
from backend.features.leases.infrastructure.repository import SqlLeaseStore
from backend.features.leases.settings import LeaseSettings


class LeaseProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> LeaseSettings:
        return LeaseSettings()

    @provide(scope=Scope.REQUEST, provides=LeaseStore)
    def store(self, session: AsyncSession) -> LeaseStore:
        return SqlLeaseStore(session)

    @provide(scope=Scope.REQUEST, provides=BrowserAllocator)
    def allocator(self, browsers: BrowserService) -> BrowserAllocator:
        return BrowserServiceAllocator(browsers)

    @provide(scope=Scope.REQUEST)
    def lease_service(
        self,
        allocator: BrowserAllocator,
        store: LeaseStore,
        settings: LeaseSettings,
    ) -> LeaseService:
        return LeaseService(allocator, store, settings)
