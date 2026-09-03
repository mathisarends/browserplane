from dishka import Provider, Scope, provide

from control_plane.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRegistry,
)
from control_plane.features.browsers.application.service import BrowserService
from control_plane.features.browsers.infrastructure.data_plane_provisioner import (
    DataPlaneBrowserProvisioner,
)
from control_plane.features.browsers.infrastructure.in_memory_registry import (
    InMemoryBrowserRegistry,
)
from control_plane.settings import ControlPlaneSettings


class BrowserProvider(Provider):
    def __init__(self, provisioner: BrowserProvisioner | None = None) -> None:
        super().__init__()
        self._provisioner = provisioner

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
