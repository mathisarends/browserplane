from dishka import Provider, Scope, provide

from backend.features.sessions.application.ports import BrowserCatalog, LeaseBroker
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.infrastructure.in_memory_control_plane import (
    InMemoryControlPlane,
)
from backend.settings import BackendSettings


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def upstream(self, settings: BackendSettings) -> InMemoryControlPlane:
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
