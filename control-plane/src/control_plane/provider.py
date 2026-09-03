from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from control_plane.provisioning import BrowserProvisioner, ComposeBrowserProvisioner
from control_plane.registry import BrowserRegistry
from control_plane.settings import ControlPlaneSettings


class ControlPlaneProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ControlPlaneSettings:
        return ControlPlaneSettings()

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(
        self, settings: ControlPlaneSettings
    ) -> ComposeBrowserProvisioner:
        return ComposeBrowserProvisioner(settings)

    @provide(scope=Scope.APP)
    async def registry(
        self, provisioner: BrowserProvisioner
    ) -> AsyncIterator[BrowserRegistry]:
        registry = BrowserRegistry(provisioner)
        await registry.start()
        try:
            yield registry
        finally:
            await registry.stop()
