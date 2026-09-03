from dishka import Provider, Scope, provide

from data_plane.settings import DataPlaneSettings


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> DataPlaneSettings:
        return DataPlaneSettings()
