from dishka import Provider, Scope, provide

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.service import SessionService


class SessionProvider(Provider):
    @provide(scope=Scope.APP)
    def session_service(
        self, browsers: BrowserService, leases: LeaseService
    ) -> SessionService:
        return SessionService(browsers, leases)
