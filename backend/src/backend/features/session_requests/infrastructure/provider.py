from dishka import Provider, Scope, provide

from backend.features.session_requests.application import (
    ControlPlane,
    SessionAcquisition,
    Wakeups,
)
from backend.features.session_requests.domain import Notifier, SessionRequestRepository
from backend.features.session_requests.infrastructure.dispatcher import Dispatcher
from backend.features.session_requests.infrastructure.notifications import (
    PostgresListener,
    PostgresNotifier,
)
from backend.features.session_requests.infrastructure.repository import (
    SqlSessionRequestRepository,
)


class SessionRequestProvider(Provider):
    scope = Scope.APP

    wakeups = provide(Wakeups)
    control_plane = provide(ControlPlane)
    acquisition = provide(SessionAcquisition)
    listener = provide(PostgresListener)

    sql_repository = provide(
        SqlSessionRequestRepository, provides=SqlSessionRequestRepository
    )

    @provide
    def repository(
        self, repository: SqlSessionRequestRepository
    ) -> SessionRequestRepository:
        return repository

    notifier = provide(PostgresNotifier, provides=Notifier)

    dispatcher = provide(Dispatcher, provides=Dispatcher)
