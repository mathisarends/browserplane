from dishka import Provider, Scope, provide

from data_plane.features.browser_state.application.ports import BrowserStateStore
from data_plane.features.browser_state.application.service import (
    BrowserStateService,
    StateStoreFactory,
)
from data_plane.features.browser_state.infrastructure.cdp_state import (
    CdpBrowserStateStore,
)
from data_plane.features.browsers.application.service import BrowserService
from data_plane.settings import DataPlaneSettings


class BrowserStateProvider(Provider):
    def __init__(self, service: BrowserStateService | None = None) -> None:
        super().__init__()
        self._service = service

    @provide(scope=Scope.APP)
    def store_factory(self, settings: DataPlaneSettings) -> StateStoreFactory:
        """Talk to the browser over its own short-lived CDP connection."""

        def build(cdp_url: str) -> BrowserStateStore:
            return CdpBrowserStateStore(cdp_url, settings)

        return build

    @provide(scope=Scope.APP)
    def browser_state_service(
        self,
        browsers: BrowserService,
        settings: DataPlaneSettings,
        store_factory: StateStoreFactory,
    ) -> BrowserStateService:
        return self._service or BrowserStateService(browsers, settings, store_factory)
