from dishka import Provider, Scope, provide

from gateway.settings import GatewaySettings


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> GatewaySettings:
        return GatewaySettings()
