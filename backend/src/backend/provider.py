from dishka import Provider, Scope, provide

from backend.settings import BackendSettings


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> BackendSettings:
        return BackendSettings()
