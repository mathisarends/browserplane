from datetime import timedelta

from dishka import Provider, Scope, provide
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.ports import (
    AuthenticationStateSnapshotRepository,
    BrowserRuntime,
    BrowserStateSnapshotRepository,
    SuspendedSessionRepository,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.infrastructure.browser_worker import (
    BrowserWorkerRuntime,
)
from backend.features.sessions.infrastructure.repository import (
    SqlAuthenticationStateSnapshotRepository,
    SqlBrowserStateSnapshotRepository,
    SqlSuspendedSessionRepository,
)
from backend.features.sessions.infrastructure.settings import SessionSettings
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings


class SessionProvider(Provider):
    def __init__(
        self,
        suspensions: SuspendedSessionRepository | None = None,
        browser_state: BrowserRuntime | None = None,
        snapshots: BrowserStateSnapshotRepository | None = None,
        authentication_snapshots: AuthenticationStateSnapshotRepository | None = None,
    ) -> None:
        super().__init__()
        self._suspensions = suspensions
        self._browser_state = browser_state
        self._snapshots = snapshots
        self._authentication_snapshots = authentication_snapshots

    @provide(scope=Scope.APP)
    def settings(self) -> SessionSettings:
        return SessionSettings()

    @provide(scope=Scope.REQUEST, provides=SuspendedSessionRepository)
    def suspensions(self, session: AsyncSession) -> SuspendedSessionRepository:
        return self._suspensions or SqlSuspendedSessionRepository(session)

    @provide(scope=Scope.APP, provides=BrowserRuntime)
    def browser_state(
        self,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
    ) -> BrowserRuntime:
        return self._browser_state or BrowserWorkerRuntime(http, settings)

    @provide(scope=Scope.REQUEST, provides=BrowserStateSnapshotRepository)
    def snapshots(self, session: AsyncSession) -> BrowserStateSnapshotRepository:
        return self._snapshots or SqlBrowserStateSnapshotRepository(session)

    @provide(scope=Scope.REQUEST, provides=AuthenticationStateSnapshotRepository)
    def authentication_snapshots(
        self, session: AsyncSession
    ) -> AuthenticationStateSnapshotRepository:
        return (
            self._authentication_snapshots
            or SqlAuthenticationStateSnapshotRepository(session)
        )

    @provide(scope=Scope.REQUEST)
    def session_service(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        suspensions: SuspendedSessionRepository,
        snapshots: BrowserStateSnapshotRepository,
        authentication_snapshots: AuthenticationStateSnapshotRepository,
        browser_state: BrowserRuntime,
        settings: SessionSettings,
    ) -> SessionService:
        return SessionService(
            browsers,
            leases,
            suspensions,
            snapshots,
            authentication_snapshots,
            browser_state,
            timedelta(seconds=settings.suspended_session_ttl_seconds),
        )
