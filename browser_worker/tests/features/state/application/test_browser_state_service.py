from collections.abc import Sequence

import pytest
from tests.fakes import FakeBrowserProcess

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.state.application.exceptions import (
    BrowserStateInvalidException,
)
from browser_worker.features.state.application.models import (
    AuthenticationState,
    BrowserState,
)
from browser_worker.features.state.application.ports import BrowserStateStore
from browser_worker.features.state.application.service import (
    BrowserStateService,
)
from browser_worker.features.state.infrastructure.settings import (
    BrowserStateSettings,
)

BROWSER_STATE = {
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
            "priority": "High",
            "sourceScheme": "Secure",
            "sourcePort": 443,
            "partitionKey": {
                "topLevelSite": "https://example.com",
                "hasCrossSiteAncestor": False,
            },
        }
    ],
    "localStorage": [
        {
            "origin": "https://example.com",
            "localStorage": [{"name": "token", "value": "abc"}],
        }
    ],
    "indexedDB": [
        {
            "origin": "https://example.com",
            "databases": [
                {
                    "name": "auth",
                    "version": 1,
                    "objectStores": [
                        {
                            "name": "tokens",
                            "keyPath": None,
                            "autoIncrement": False,
                            "indexes": [],
                            "records": [{"key": "user", "value": "secret"}],
                        }
                    ],
                }
            ],
        }
    ],
}


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


async def _running_service(
    store: FakeStore,
    *,
    max_tabs: int | None = None,
) -> BrowserStateService:
    browsers = BrowserService(FakeBrowserProcess())
    await browsers.create(0)
    service = BrowserStateService(
        browsers,
        max_tabs
        if max_tabs is not None
        else BrowserStateSettings(_env_file=None).max_tabs,
        lambda _: store,
    )
    return service


@pytest.mark.asyncio
async def test_state_survives_a_mount_and_capture_roundtrip() -> None:
    service = await _running_service(FakeStore())

    state = BrowserState.model_validate(BROWSER_STATE)

    await service.mount_browser(state)
    captured = await service.capture_browser()

    assert captured.model_dump(mode="json", by_alias=True) == BROWSER_STATE


@pytest.mark.asyncio
async def test_authentication_survives_a_mount_and_capture_roundtrip() -> None:
    service = await _running_service(FakeStore())
    state = AuthenticationState.model_validate(AUTHENTICATION_STATE)

    await service.mount_authentication(state)
    captured = await service.capture_authentication()

    assert captured.model_dump(mode="json", by_alias=True) == AUTHENTICATION_STATE


@pytest.mark.asyncio
async def test_active_tab_index_outside_the_tabs_is_rejected() -> None:
    service = await _running_service(FakeStore())
    state = BrowserState(
        tabs=[{"url": "https://a.example"}, {"url": "https://b.example"}],
        active_tab_index=3,
    )

    with pytest.raises(BrowserStateInvalidException):
        await service.mount_browser(state)


@pytest.mark.asyncio
async def test_non_web_tab_url_is_rejected() -> None:
    service = await _running_service(FakeStore())
    state = BrowserState(tabs=[{"url": "file:///etc/passwd"}])

    with pytest.raises(BrowserStateInvalidException):
        await service.mount_browser(state)


@pytest.mark.asyncio
async def test_browser_state_with_too_many_tabs_is_rejected() -> None:
    service = await _running_service(FakeStore(), max_tabs=1)
    state = BrowserState(
        tabs=[{"url": "https://a.example"}, {"url": "https://b.example"}]
    )

    with pytest.raises(BrowserStateInvalidException):
        await service.mount_browser(state)


@pytest.mark.asyncio
@pytest.mark.parametrize("origin", ["example.com", "https://example.com/path"])
async def test_capture_rejects_values_that_are_not_origins(origin: str) -> None:
    service = await _running_service(FakeStore())

    with pytest.raises(BrowserStateInvalidException):
        await service.capture_authentication((origin,))
