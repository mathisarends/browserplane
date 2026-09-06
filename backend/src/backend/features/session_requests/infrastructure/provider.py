from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.features.leases.settings import LeaseSettings
from backend.features.session_requests.application.acquisition import SessionAcquisition
from backend.features.session_requests.application.control_plane import ControlPlane
from backend.features.session_requests.application.ports import (
    Notifier,
    SessionRequestRepository,
)
from backend.features.session_requests.application.wakeups import Wakeups
from backend.features.session_requests.infrastructure.dispatcher import Dispatcher
from backend.features.session_requests.infrastructure.notifications import (
    PostgresListener,
    PostgresNotifier,
)
from backend.features.session_requests.infrastructure.repository import (
    SqlSessionRequestRepository,
)
from backend.features.sessions.application.ports import BrowserRuntime
from backend.features.sessions.application.service import SessionService
from backend.infrastructure.database.settings import DatabaseSettings
from backend.shared.unit_of_work import UnitOfWork


class SessionRequestProvider(Provider):
    scope = Scope.APP

    wakeups = provide(Wakeups)
    control_plane = provide(ControlPlane)
    acquisition = provide(SessionAcquisition)
    listener = provide(PostgresListener)

    @provide
    def sql_repository(
        self, factory: async_sessionmaker[AsyncSession], settings: LeaseSettings
    ) -> SqlSessionRequestRepository:
        return SqlSessionRequestRepository(factory, settings)

    @provide
    def repository(
        self, repository: SqlSessionRequestRepository
    ) -> SessionRequestRepository:
        return repository

    @provide
    def notifier(self, factory: async_sessionmaker[AsyncSession]) -> Notifier:
        return PostgresNotifier(factory)

    @provide
    def dispatcher(
        self,
        sessions: UnitOfWork[SessionService],
        repository: SqlSessionRequestRepository,
        provisioner: BrowserProvisioner,
        runtime: BrowserRuntime,
        settings: DatabaseSettings,
        pool: BrowserPoolSettings,
        wakeups: Wakeups,
        leases: LeaseSettings,
    ) -> Dispatcher:
        return Dispatcher(
            sessions, repository, provisioner, runtime, settings, pool, wakeups, leases
        )
