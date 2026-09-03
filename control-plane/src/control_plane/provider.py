from dishka import Provider, Scope, provide

from control_plane.settings import ControlPlaneSettings


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ControlPlaneSettings:
        return ControlPlaneSettings()
