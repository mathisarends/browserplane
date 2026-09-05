from datetime import timedelta

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from backend.browser_tunnel.presentation.session import BrowserTunnel
from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.ports import (
    BrowserStateGateway,
    BrowserStateSnapshotRepository,
    SuspendedSessionRepository,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.infrastructure.data_plane_gateway import (
    DataPlaneBrowserStateGateway,
)
from backend.features.sessions.infrastructure.repository import (
    SqlBrowserStateSnapshotRepository,
    SqlSuspendedSessionRepository,
)
from backend.settings import BackendSettings


class SessionProvider(Provider):
    def __init__(
        self,
        suspensions: SuspendedSessionRepository | None = None,
        browser_state: BrowserStateGateway | None = None,
        snapshots: BrowserStateSnapshotRepository | None = None,
    ) -> None:
        super().__init__()
        self._suspensions = suspensions
        self._browser_state = browser_state
        self._snapshots = snapshots

    @provide(scope=Scope.REQUEST, provides=SuspendedSessionRepository)
    def suspensions(self, session: AsyncSession) -> SuspendedSessionRepository:
        return self._suspensions or SqlSuspendedSessionRepository(session)

    @provide(scope=Scope.APP, provides=BrowserStateGateway)
    def browser_state(self) -> BrowserStateGateway:
        return self._browser_state or DataPlaneBrowserStateGateway()

    @provide(scope=Scope.REQUEST, provides=BrowserStateSnapshotRepository)
    def snapshots(self, session: AsyncSession) -> BrowserStateSnapshotRepository:
        return self._snapshots or SqlBrowserStateSnapshotRepository(session)

    @provide(scope=Scope.APP)
    def browser_tunnel(self, settings: BackendSettings) -> BrowserTunnel:
        return BrowserTunnel(
            width=settings.browser_width,
            height=settings.browser_height,
        )

    @provide(scope=Scope.REQUEST)
    def session_service(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        suspensions: SuspendedSessionRepository,
        snapshots: BrowserStateSnapshotRepository,
        browser_state: BrowserStateGateway,
        settings: BackendSettings,
    ) -> SessionService:
        return SessionService(
            browsers,
            leases,
            suspensions,
            snapshots,
            browser_state,
            timedelta(seconds=settings.suspended_session_ttl_seconds),
        )
