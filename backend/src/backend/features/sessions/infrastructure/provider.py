from datetime import timedelta

from dishka import AsyncContainer, Provider, Scope, provide

from backend.features.browsers.application import BrowserService
from backend.features.leases.application import LeaseService, LeaseSettings
from backend.features.sessions.application import SessionLeaseKeeper, SessionService
from backend.features.sessions.domain import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    BrowserRuntime,
    SessionRepository,
)
from backend.features.sessions.infrastructure.browser_worker import (
    BrowserWorkerRuntime,
)
from backend.features.sessions.infrastructure.encryption import (
    AuthenticationStateCipher,
)
from backend.features.sessions.infrastructure.repository import (
    SqlAuthenticationProfileRepository,
    SqlBrowserCheckpointRepository,
    SqlSessionRepository,
)
from backend.features.sessions.infrastructure.settings import SessionSettings
from backend.infrastructure.database.unit_of_work import ScopedUnitOfWork
from backend.shared.unit_of_work import UnitOfWork


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def unit_of_work(self, container: AsyncContainer) -> UnitOfWork[SessionService]:
        """For callers outside an HTTP request, and for those who must not hold one."""
        return ScopedUnitOfWork(container, SessionService)

    @provide(scope=Scope.APP)
    def lease_keeper(
        self, sessions: UnitOfWork[SessionService], settings: LeaseSettings
    ) -> SessionLeaseKeeper:
        return SessionLeaseKeeper(sessions, settings.heartbeat_interval_seconds)

    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> SessionSettings:
        return SessionSettings()

    @provide(scope=Scope.APP)
    def authentication_state_cipher(
        self, settings: SessionSettings
    ) -> AuthenticationStateCipher:
        return AuthenticationStateCipher(
            settings.authentication_state_encryption_key.get_secret_value()
        )

    sessions = provide(
        SqlSessionRepository, scope=Scope.REQUEST, provides=SessionRepository
    )

    browser_runtime = provide(
        BrowserWorkerRuntime, scope=Scope.APP, provides=BrowserRuntime
    )

    checkpoints = provide(
        SqlBrowserCheckpointRepository,
        scope=Scope.REQUEST,
        provides=BrowserCheckpointRepository,
    )

    authentication_profiles = provide(
        SqlAuthenticationProfileRepository,
        scope=Scope.REQUEST,
        provides=AuthenticationProfileRepository,
    )

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
