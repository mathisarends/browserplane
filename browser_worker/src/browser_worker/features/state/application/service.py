from collections.abc import Callable, Sequence
from urllib.parse import urlsplit
from uuid import UUID

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.state.application.exceptions import (
    BrowserStateInvalidException,
)
from browser_worker.features.state.application.models import (
    AuthenticationState,
    BrowserState,
)
from browser_worker.features.state.application.ports import BrowserStateStore

StateStoreFactory = Callable[[str], BrowserStateStore]

WEB_SCHEMES = frozenset({"http", "https"})


class BrowserStateService:
    """Read the worker browser's state and mount a captured one back onto it.

    Both operations are stateless towards the worker: the state lives in the
    browser, so a mount may run as often as a caller likes.
    """

    def __init__(
        self,
        browsers: BrowserService,
        max_tabs: int,
        store_factory: StateStoreFactory,
    ) -> None:
        self._browsers = browsers
        self._max_tabs = max_tabs
        self._store_factory = store_factory

    async def capture_authentication(
        self,
        browser_id: UUID,
        origins: Sequence[str] = (),
    ) -> AuthenticationState:
        for origin in origins:
            _validate_origin(origin)
        return await self._store(browser_id).capture_authentication(
            extra_origins=origins
        )

    async def mount_authentication(
        self, browser_id: UUID, state: AuthenticationState
    ) -> None:
        for origin in state.local_storage:
            _validate_origin(origin.origin)
        await self._store(browser_id).restore_authentication(state)

    async def capture_browser(self, browser_id: UUID) -> BrowserState:
        return await self._store(browser_id).capture_browser()

    async def mount_browser(self, browser_id: UUID, state: BrowserState) -> None:
        self._validate_browser(state)
        await self._store(browser_id).restore_browser(state)

    def _store(self, browser_id: UUID) -> BrowserStateStore:
        # Raises BrowserNotFoundException for an id the worker does not run.
        return self._store_factory(self._browsers.upstream_cdp_url(browser_id))

    def _validate_browser(self, state: BrowserState) -> None:
        max_tabs = self._max_tabs
        if len(state.tabs) > max_tabs:
            raise BrowserStateInvalidException(
                f"Browser state has more than {max_tabs} tabs"
            )
        for tab in state.tabs:
            _validate_tab_url(tab.url)
        if state.tabs and not 0 <= state.active_tab_index < len(state.tabs):
            raise BrowserStateInvalidException(
                "active_tab_index does not point at one of the tabs"
            )


def _validate_tab_url(url: str) -> None:
    if urlsplit(url).scheme not in WEB_SCHEMES:
        raise BrowserStateInvalidException(
            f"Tab url must be http or https, got {url!r}"
        )


def _validate_origin(origin: str) -> None:
    parts = urlsplit(origin)
    if parts.scheme not in WEB_SCHEMES or not parts.netloc or parts.path:
        raise BrowserStateInvalidException(
            f"Origin must be scheme://host, got {origin!r}"
        )
