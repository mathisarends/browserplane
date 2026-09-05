from collections.abc import Callable, Sequence
from urllib.parse import urlsplit
from uuid import UUID

from data_plane.features.browser_state.application.exceptions import (
    BrowserStateInvalidException,
)
from data_plane.features.browser_state.application.models import BrowserState
from data_plane.features.browser_state.application.ports import BrowserStateStore
from data_plane.features.browsers.application.service import BrowserService
from data_plane.settings import DataPlaneSettings

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
        settings: DataPlaneSettings,
        store_factory: StateStoreFactory,
    ) -> None:
        self._browsers = browsers
        self._settings = settings
        self._store_factory = store_factory

    async def capture(
        self,
        browser_id: UUID,
        origins: Sequence[str] = (),
    ) -> BrowserState:
        for origin in origins:
            _validate_origin(origin)
        return await self._store(browser_id).capture(extra_origins=origins)

    async def mount(self, browser_id: UUID, state: BrowserState) -> None:
        self._validate(state)
        await self._store(browser_id).restore(state)

    def _store(self, browser_id: UUID) -> BrowserStateStore:
        # Raises BrowserNotFoundException for an id the worker does not run.
        return self._store_factory(self._browsers.upstream_cdp_url(browser_id))

    def _validate(self, state: BrowserState) -> None:
        max_tabs = self._settings.browser_state_max_tabs
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
        for origin in state.authentication.origins:
            _validate_origin(origin.origin)


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
