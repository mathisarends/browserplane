from dishka import Provider, Scope, provide

from gateway.features.sessions.application.ports import BrowserCatalog, LeaseBroker
from gateway.features.sessions.application.service import SessionService
from gateway.features.sessions.infrastructure.in_memory_control_plane import (
    InMemoryControlPlane,
)
from gateway.settings import GatewaySettings


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def upstream(self, settings: GatewaySettings) -> InMemoryControlPlane:
        return InMemoryControlPlane(settings)

    @provide(scope=Scope.APP, provides=BrowserCatalog)
    def catalog(self, upstream: InMemoryControlPlane) -> BrowserCatalog:
        return upstream

    @provide(scope=Scope.APP, provides=LeaseBroker)
    def leases(self, upstream: InMemoryControlPlane) -> LeaseBroker:
        return upstream

    @provide(scope=Scope.APP)
    def session_service(
        self, catalog: BrowserCatalog, leases: LeaseBroker
    ) -> SessionService:
        return SessionService(catalog, leases)
