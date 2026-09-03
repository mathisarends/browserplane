from dishka import Provider, Scope, provide

from control_plane.provisioning import (
    BrowserProvisioner,
    DataPlaneBrowserProvisioner,
)
from control_plane.registry import BrowserRegistry, InMemoryBrowserRegistry
from control_plane.services import BrowserService, LeaseService
from control_plane.settings import ControlPlaneSettings


class ControlPlaneProvider(Provider):
    def __init__(self, provisioner: BrowserProvisioner | None = None) -> None:
        super().__init__()
        self._provisioner = provisioner

    @provide(scope=Scope.APP)
    def settings(self) -> ControlPlaneSettings:
        return ControlPlaneSettings()

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(self, settings: ControlPlaneSettings) -> BrowserProvisioner:
        return self._provisioner or DataPlaneBrowserProvisioner(settings)

    @provide(scope=Scope.APP, provides=BrowserRegistry)
    def registry(self) -> BrowserRegistry:
        return InMemoryBrowserRegistry()

    @provide(scope=Scope.APP)
    def browser_service(
        self, provisioner: BrowserProvisioner, registry: BrowserRegistry
    ) -> BrowserService:
        return BrowserService(provisioner, registry)

    @provide(scope=Scope.APP)
    def lease_service(self, registry: BrowserRegistry) -> LeaseService:
        return LeaseService(registry)
