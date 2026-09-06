from dishka import AsyncContainer, Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.features.browser_requests.application import ControlPlane, Notifier, RequestRepository, Wakeups
from backend.features.browser_requests.infrastructure.dispatcher import Dispatcher
from backend.features.browser_requests.infrastructure.notifications import PostgresListener, PostgresNotifier
from backend.features.browser_requests.infrastructure.repository import SqlRequestRepository
from backend.features.browsers.application.ports import BrowserProvisioner
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.features.leases.settings import LeaseSettings
from backend.features.sessions.application.ports import BrowserRuntime
from backend.infrastructure.database.settings import DatabaseSettings


class RequestProvider(Provider):
    scope = Scope.APP

    wakeups = provide(Wakeups)
    control_plane = provide(ControlPlane)
    listener = provide(PostgresListener)

    @provide
    def sql_repository(self, factory: async_sessionmaker[AsyncSession], settings: LeaseSettings) -> SqlRequestRepository:
        return SqlRequestRepository(factory, settings)

    @provide
    def repository(self, repository: SqlRequestRepository) -> RequestRepository:
        return repository

    @provide
    def notifier(self, factory: async_sessionmaker[AsyncSession]) -> Notifier:
        return PostgresNotifier(factory)

    @provide
    def dispatcher(self, container: AsyncContainer, repository: SqlRequestRepository,
                   provisioner: BrowserProvisioner, runtime: BrowserRuntime,
                   settings: DatabaseSettings, pool: BrowserPoolSettings, wakeups: Wakeups,
                   leases: LeaseSettings) -> Dispatcher:
        return Dispatcher(container, repository, provisioner, runtime, settings, pool, wakeups, leases)
