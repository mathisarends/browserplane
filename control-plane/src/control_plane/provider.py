from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from control_plane.provisioning import (
    BrowserProvisioner,
    DataPlaneBrowserProvisioner,
)
from control_plane.registry import BrowserRegistry
from control_plane.settings import ControlPlaneSettings


class ControlPlaneProvider(Provider):
    def __init__(self, provisioner: BrowserProvisioner | None = None) -> None:
        super().__init__()
        self._provisioner = provisioner

    @provide(scope=Scope.APP)
    def settings(self) -> ControlPlaneSettings:
        return ControlPlaneSettings()

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(
        self, settings: ControlPlaneSettings
    ) -> BrowserProvisioner:
        return self._provisioner or DataPlaneBrowserProvisioner(settings)

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
