from dishka import Provider, Scope, provide

from browser_worker.features.health.application.service import HealthService


class HealthProvider(Provider):
    health_service = provide(HealthService, scope=Scope.APP)
