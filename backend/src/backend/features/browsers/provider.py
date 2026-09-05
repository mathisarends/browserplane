from dishka import Provider, Scope, provide

from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRegistry,
)
from backend.features.browsers.application.service import BrowserService
from backend.features.browsers.infrastructure.data_plane_provisioner import (
    DataPlaneBrowserProvisioner,
)
from backend.features.browsers.infrastructure.in_memory_registry import (
    InMemoryBrowserRegistry,
)
from backend.settings import BackendSettings


class BrowserProvider(Provider):
    def __init__(self, provisioner: BrowserProvisioner | None = None) -> None:
        super().__init__()
        self._provisioner = provisioner

    @provide(scope=Scope.APP, provides=BrowserProvisioner)
    def provisioner(self, settings: BackendSettings) -> BrowserProvisioner:
        return self._provisioner or DataPlaneBrowserProvisioner(settings)

    @provide(scope=Scope.APP, provides=BrowserRegistry)
    def registry(self) -> BrowserRegistry:
        return InMemoryBrowserRegistry()

    @provide(scope=Scope.APP)
    def browser_service(
        self, provisioner: BrowserProvisioner, registry: BrowserRegistry
    ) -> BrowserService:
        return BrowserService(provisioner, registry)
