from datetime import timedelta

from dishka import AsyncContainer, Provider, Scope, provide
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.service import LeaseService
from backend.features.leases.settings import LeaseSettings
from backend.features.sessions.application.ports import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    BrowserRuntime,
    SessionRepository,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.infrastructure.browser_worker import (
    BrowserWorkerRuntime,
)
from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.features.sessions.infrastructure.lease_keeper import SessionLeaseKeeper
from backend.features.sessions.infrastructure.repository import (
    SqlAuthenticationProfileRepository,
    SqlBrowserCheckpointRepository,
    SqlSessionRepository,
)
from backend.features.sessions.infrastructure.settings import SessionSettings
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from backend.infrastructure.database.unit_of_work import ScopedUnitOfWork
from backend.shared.unit_of_work import UnitOfWork


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def unit_of_work(self, container: AsyncContainer) -> UnitOfWork[SessionService]:
        """For callers outside an HTTP request, and for those who must not hold one."""
        return ScopedUnitOfWork(container, SessionService)

    @provide(scope=Scope.APP)
    def lease_keeper(
        self, container: AsyncContainer, settings: LeaseSettings
    ) -> SessionLeaseKeeper:
        return SessionLeaseKeeper(container, settings.heartbeat_interval_seconds)

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

    @provide(scope=Scope.REQUEST, provides=SessionRepository)
    def sessions(self, session: AsyncSession) -> SessionRepository:
        return SqlSessionRepository(session)

    @provide(scope=Scope.APP, provides=BrowserRuntime)
    def browser_runtime(
        self,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
    ) -> BrowserRuntime:
        return BrowserWorkerRuntime(http, settings)

    @provide(scope=Scope.REQUEST, provides=BrowserCheckpointRepository)
    def checkpoints(self, session: AsyncSession) -> BrowserCheckpointRepository:
        return SqlBrowserCheckpointRepository(session)

    @provide(scope=Scope.REQUEST, provides=AuthenticationProfileRepository)
    def authentication_profiles(
        self, session: AsyncSession, cipher: AuthenticationStateCipher
    ) -> AuthenticationProfileRepository:
        return SqlAuthenticationProfileRepository(session, cipher)

    @provide(scope=Scope.REQUEST)
    def session_service(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        sessions: SessionRepository,
        checkpoints: BrowserCheckpointRepository,
        authentication_profiles: AuthenticationProfileRepository,
        browser_runtime: BrowserRuntime,
        settings: SessionSettings,
    ) -> SessionService:
        return SessionService(
            browsers=browsers,
            leases=leases,
            sessions=sessions,
            checkpoints=checkpoints,
            authentication_profiles=authentication_profiles,
            browser_state=browser_runtime,
            suspension_ttl=timedelta(seconds=settings.suspended_session_ttl_seconds),
        )
