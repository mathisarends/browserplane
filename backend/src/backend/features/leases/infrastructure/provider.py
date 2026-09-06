from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.ports import BrowserAllocator, LeaseStore
from backend.features.leases.application.service import LeaseService
from backend.features.leases.infrastructure.browser_service_allocator import (
    BrowserServiceAllocator,
)
from backend.features.leases.infrastructure.repository import SqlLeaseStore


class LeaseProvider(Provider):
    def __init__(self, store: LeaseStore | None = None) -> None:
        super().__init__()
        self._store = store

    @provide(scope=Scope.REQUEST, provides=LeaseStore)
    def store(self, session: AsyncSession) -> LeaseStore:
        return self._store or SqlLeaseStore(session)

    @provide(scope=Scope.REQUEST, provides=BrowserAllocator)
    def allocator(self, browsers: BrowserService) -> BrowserAllocator:
        return BrowserServiceAllocator(browsers)

    @provide(scope=Scope.REQUEST)
    def lease_service(
        self, allocator: BrowserAllocator, store: LeaseStore
    ) -> LeaseService:
        return LeaseService(allocator, store)
