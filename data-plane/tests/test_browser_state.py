from collections.abc import Sequence
from uuid import uuid4

import pytest

from data_plane.features.browser.application.ports import BrowserProcess
from data_plane.features.browser.application.service import BrowserService
from data_plane.features.browser.state.application.exceptions import (
    BrowserStateInvalidException,
)
from data_plane.features.browser.state.application.models import (
    AuthenticationState,
    BrowserState,
)
from data_plane.features.browser.state.application.ports import BrowserStateStore
from data_plane.features.browser.state.application.service import BrowserStateService
from data_plane.features.browser.state.presentation.mapper import (
    to_authentication_state,
    to_authentication_state_response,
    to_browser_state,
    to_browser_state_response,
)
from data_plane.features.browser.state.presentation.schemas import (
    AuthenticationStateSchema,
    BrowserStateSchema,
)
from data_plane.settings import DataPlaneSettings

PLAYWRIGHT_STATE = {
    "tabs": [
        {
            "url": "https://example.com/inbox",
            "scroll": {"x": 0, "y": 240},
            "sessionStorage": [{"name": "draft", "value": "hello"}],
        }
    ],
    "active_tab_index": 0,
}

AUTHENTICATION_STATE = {
    "cookies": [
        {
            "name": "session",
            "value": "secret",
            "domain": "example.com",
            "path": "/",
            "expires": None,
            "httpOnly": True,
            "secure": True,
            "sameSite": "Lax",
        }
    ],
    "origins": [
        {
            "origin": "https://example.com",
            "localStorage": [{"name": "token", "value": "abc"}],
        }
    ],
}


class FakeProcess(BrowserProcess):
    async def start(self) -> str:
        return "ws://chromium/devtools/browser/test"

    async def stop(self) -> None:
        return None


class FakeStore(BrowserStateStore):
    """Hand back whatever was mounted last, so a roundtrip is observable."""

    def __init__(self) -> None:
        self.browser_state = BrowserState()
        self.authentication_state = AuthenticationState()

    async def capture_authentication(
        self, extra_origins: Sequence[str] = ()
    ) -> AuthenticationState:
        return self.authentication_state

    async def restore_authentication(self, state: AuthenticationState) -> None:
        self.authentication_state = state

    async def capture_browser(self) -> BrowserState:
        return self.browser_state

    async def restore_browser(self, state: BrowserState) -> None:
        self.browser_state = state


async def _running_service(store: FakeStore) -> tuple[BrowserStateService, object]:
    settings = DataPlaneSettings()
    browsers = BrowserService(settings, lambda _: FakeProcess())
    browser = await browsers.create(uuid4())
    return BrowserStateService(browsers, settings, lambda _: store), browser.id


@pytest.mark.asyncio
async def test_state_survives_a_mount_and_capture_roundtrip() -> None:
    service, browser_id = await _running_service(FakeStore())

    state = to_browser_state(BrowserStateSchema(**PLAYWRIGHT_STATE))

    await service.mount_browser(browser_id, state)
    captured = to_browser_state_response(await service.capture_browser(browser_id))

    assert captured.model_dump(by_alias=True) == PLAYWRIGHT_STATE


@pytest.mark.asyncio
async def test_authentication_survives_a_mount_and_capture_roundtrip() -> None:
    service, browser_id = await _running_service(FakeStore())
    state = to_authentication_state(AuthenticationStateSchema(**AUTHENTICATION_STATE))

    await service.mount_authentication(browser_id, state)
    captured = to_authentication_state_response(
        await service.capture_authentication(browser_id)
    )

    assert captured.model_dump(by_alias=True) == AUTHENTICATION_STATE


@pytest.mark.asyncio
async def test_active_tab_index_outside_the_tabs_is_rejected() -> None:
    service, browser_id = await _running_service(FakeStore())
    state = BrowserStateSchema(
        tabs=[{"url": "https://a.example"}, {"url": "https://b.example"}],
        active_tab_index=3,
    )

    with pytest.raises(BrowserStateInvalidException):
        await service.mount_browser(browser_id, to_browser_state(state))


@pytest.mark.asyncio
async def test_non_web_tab_url_is_rejected() -> None:
    service, browser_id = await _running_service(FakeStore())
    state = BrowserStateSchema(tabs=[{"url": "file:///etc/passwd"}])

    with pytest.raises(BrowserStateInvalidException):
        await service.mount_browser(browser_id, to_browser_state(state))
