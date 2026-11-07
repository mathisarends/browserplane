from dishka import Provider, Scope, provide

from browser_worker.features.browser.application import BrowserService
from browser_worker.features.state.application import (
    BrowserStateService,
    BrowserStateStore,
    StateStoreFactory,
)
from browser_worker.features.state.infrastructure.cdp import (
    CdpBrowserStateStore,
)
from browser_worker.features.state.infrastructure.settings import (
    BrowserStateSettings,
)


class BrowserStateProvider(Provider):
    def __init__(self, service: BrowserStateService | None = None) -> None:
        super().__init__()
        self._service = service

    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> BrowserStateSettings:
        return BrowserStateSettings()

    @provide(scope=Scope.APP)
    def store_factory(self, settings: BrowserStateSettings) -> StateStoreFactory:
        """Talk to the browser over its own short-lived CDP connection."""

        def build(cdp_url: str) -> BrowserStateStore:
            return CdpBrowserStateStore(cdp_url, settings)

        return build

    @provide(scope=Scope.APP)
    def browser_state_service(
        self,
        browsers: BrowserService,
        settings: BrowserStateSettings,
        store_factory: StateStoreFactory,
    ) -> BrowserStateService:
        return self._service or BrowserStateService(
            browsers,
            settings.max_tabs,
            store_factory,
        )
