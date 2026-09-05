from dishka import Provider, Scope, provide

from backend.features.admin.application.service import AdminService
from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.service import SessionService


class AdminProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def admin_service(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        sessions: SessionService,
    ) -> AdminService:
        return AdminService(browsers, leases, sessions)
