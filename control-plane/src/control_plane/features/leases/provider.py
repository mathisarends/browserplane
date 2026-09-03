from dishka import Provider, Scope, provide

from control_plane.features.browsers.application.service import BrowserService
from control_plane.features.leases.application.ports import BrowserAllocator, LeaseStore
from control_plane.features.leases.application.service import LeaseService
from control_plane.features.leases.infrastructure.browser_service_allocator import (
    BrowserServiceAllocator,
)
from control_plane.features.leases.infrastructure.in_memory_store import (
    InMemoryLeaseStore,
)


class LeaseProvider(Provider):
    @provide(scope=Scope.APP, provides=LeaseStore)
    def store(self) -> LeaseStore:
        return InMemoryLeaseStore()

    @provide(scope=Scope.APP, provides=BrowserAllocator)
    def allocator(self, browsers: BrowserService) -> BrowserAllocator:
        return BrowserServiceAllocator(browsers)

    @provide(scope=Scope.APP)
    def lease_service(
        self, allocator: BrowserAllocator, store: LeaseStore
    ) -> LeaseService:
        return LeaseService(allocator, store)
