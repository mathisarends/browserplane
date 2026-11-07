from dishka import Provider, Scope, provide

from backend.features.admin.application import AdminService


class AdminProvider(Provider):
    admin_service = provide(AdminService, scope=Scope.REQUEST, provides=AdminService)
