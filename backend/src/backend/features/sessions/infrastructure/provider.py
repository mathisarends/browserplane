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
from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.features.sessions.infrastructure.repository import (
    SqlAuthenticationStateSnapshotRepository,
    SqlBrowserStateSnapshotRepository,
    SqlSuspendedSessionRepository,
)
from backend.features.sessions.infrastructure.settings import SessionSettings
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> SessionSettings:
        return SessionSettings()

    @provide(scope=Scope.APP)
    def authentication_state_cipher(
        self, settings: SessionSettings
    ) -> AuthenticationStateCipher:
        return AuthenticationStateCipher(
            settings.authentication_state_encryption_key.get_secret_value()
        )

    @provide(scope=Scope.REQUEST, provides=SuspendedSessionRepository)
    def suspensions(
        self, session: AsyncSession, cipher: AuthenticationStateCipher
    ) -> SuspendedSessionRepository:
        return SqlSuspendedSessionRepository(session, cipher)

    @provide(scope=Scope.APP, provides=BrowserRuntime)
    def browser_runtime(
        self,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
    ) -> BrowserRuntime:
        return BrowserWorkerRuntime(http, settings)

    @provide(scope=Scope.REQUEST, provides=BrowserStateSnapshotRepository)
    def snapshots(self, session: AsyncSession) -> BrowserStateSnapshotRepository:
        return SqlBrowserStateSnapshotRepository(session)

    @provide(scope=Scope.REQUEST, provides=AuthenticationStateSnapshotRepository)
    def authentication_snapshots(
        self, session: AsyncSession, cipher: AuthenticationStateCipher
    ) -> AuthenticationStateSnapshotRepository:
        return SqlAuthenticationStateSnapshotRepository(session, cipher)

    @provide(scope=Scope.REQUEST)
    def session_service(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        suspensions: SuspendedSessionRepository,
        snapshots: BrowserStateSnapshotRepository,
        authentication_snapshots: AuthenticationStateSnapshotRepository,
        browser_runtime: BrowserRuntime,
        settings: SessionSettings,
    ) -> SessionService:
        return SessionService(
            browsers=browsers,
            leases=leases,
            suspensions=suspensions,
            snapshots=snapshots,
            authentication_snapshots=authentication_snapshots,
            browser_state=browser_runtime,
            suspension_ttl=timedelta(seconds=settings.suspended_session_ttl_seconds),
        )
