from dishka import Provider, Scope, provide

from data_plane.settings import DataPlaneSettings
from data_plane.workspace import Workspace


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> DataPlaneSettings:
        return DataPlaneSettings()

    @provide(scope=Scope.APP)
    def workspace(self, settings: DataPlaneSettings) -> Workspace:
        workspace = Workspace.from_settings(settings)
        workspace.ensure()
        return workspace
