from dishka import Provider, Scope, provide

from backend.features.leases.application import LeaseService, LeaseSettings
from backend.features.leases.domain import BrowserAllocator, LeaseStore
from backend.features.leases.infrastructure.browser_service_allocator import (
    BrowserServiceAllocator,
)
from backend.features.leases.infrastructure.repository import SqlLeaseStore
from backend.features.leases.infrastructure.settings import EnvironmentLeaseSettings


class LeaseProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> LeaseSettings:
        return EnvironmentLeaseSettings()

    store = provide(SqlLeaseStore, scope=Scope.REQUEST, provides=LeaseStore)

    allocator = provide(
        BrowserServiceAllocator, scope=Scope.REQUEST, provides=BrowserAllocator
    )

    lease_service = provide(LeaseService, scope=Scope.REQUEST, provides=LeaseService)
