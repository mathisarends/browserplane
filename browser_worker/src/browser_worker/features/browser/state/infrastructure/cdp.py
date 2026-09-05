import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Sequence
from contextlib import asynccontextmanager, suppress
from functools import partial
from typing import Any
from urllib.parse import urlsplit

from cdpify import CDPSession, Client
from cdpify.domains.domstorage.types import StorageId
from cdpify.domains.network.types import CookieParam
from cdpify.domains.page.events import LoadEventFiredEvent, PageEvent
from cdpify.domains.target.types import TargetInfo

from browser_worker.features.browser.state.application.exceptions import (
    BrowserStateFailedException,
)
from browser_worker.features.browser.state.application.models import (
    AuthenticationState,
    BrowserCookie,
    BrowserOriginState,
    BrowserState,
    BrowserTabState,
    ScrollPosition,
    StorageItem,
)
from browser_worker.features.browser.state.application.ports import BrowserStateStore
from browser_worker.features.browser.state.infrastructure.settings import (
    BrowserStateSettings,
)

logger = logging.getLogger(__name__)

_WEB_SCHEMES = frozenset({"http", "https"})
_BLANK_URL = "about:blank"


class CdpBrowserStateStore(BrowserStateStore):
    def __init__(self, cdp_url: str, settings: BrowserStateSettings) -> None:
        self._cdp_url = cdp_url
        self._settings = settings

    async def capture_authentication(
        self, extra_origins: Sequence[str] = ()
    ) -> AuthenticationState:
        return await self._execute(
            partial(_capture_authentication_state, extra_origins=extra_origins),
            failure="Could not read the browser state",
        )

    async def restore_authentication(self, state: AuthenticationState) -> None:
        await self._execute(
            partial(_restore_authentication, auth=state),
            failure="Could not mount the browser state",
        )

    async def capture_browser(self) -> BrowserState:
        return await self._execute(
            _capture_browser_state,
            failure="Could not read the browser state",
        )

    async def restore_browser(self, state: BrowserState) -> None:
        await self._execute(
            partial(_restore_browser_state, state=state, settings=self._settings),
            failure="Could not mount the browser state",
        )

    async def _execute[T](
        self,
        operation: Callable[[Client], Awaitable[T]],
        *,
        failure: str,
    ) -> T:
        try:
            async with Client(self._cdp_url) as client:
                return await operation(client)
        except BrowserStateFailedException:
            raise
        except Exception as error:
            raise BrowserStateFailedException(
                f"{failure}: {type(error).__name__}"
            ) from error


async def _capture_authentication_state(
    client: Client, *, extra_origins: Sequence[str]
) -> AuthenticationState:
    targets = await _page_targets(client)
    cookies, origins = await asyncio.gather(
        _capture_cookies(client),
        _capture_origins(client, _origins_of(targets) | set(extra_origins)),
    )
    return AuthenticationState(cookies=cookies, origins=origins)


async def _capture_browser_state(client: Client) -> BrowserState:
    targets = await _page_targets(client)
    tabs, active_tab_index = await _capture_tabs(client, targets)
    return BrowserState(tabs=tabs, active_tab_index=active_tab_index)


async def _restore_browser_state(
    client: Client, *, state: BrowserState, settings: BrowserStateSettings
) -> None:
    if state.tabs:
        await _restore_tabs(client, state, settings)


async def _page_targets(client: Client) -> tuple[TargetInfo, ...]:
    targets = await client.target.get_targets()
    return tuple(target for target in targets.target_infos if target.type == "page")


def _origins_of(targets: Iterable[TargetInfo]) -> set[str]:
    return {origin for target in targets if (origin := _to_origin(target.url))}


def _to_origin(url: str) -> str | None:
    parts = urlsplit(url)
    if parts.scheme not in _WEB_SCHEMES or not parts.netloc:
        return None
    return f"{parts.scheme}://{parts.netloc}"


async def _capture_cookies(client: Client) -> tuple[BrowserCookie, ...]:
    """Read the whole browser context, not just one tab's cookies."""
    result = await client.storage.get_cookies()
    return tuple(
        BrowserCookie(
            name=cookie.name,
            value=cookie.value,
            domain=cookie.domain,
            path=cookie.path,
            # CDP reports session cookies as expires -1.
            expires=cookie.expires if cookie.expires > 0 else None,
            http_only=cookie.http_only,
            secure=cookie.secure,
            same_site=cookie.same_site,
        )
        for cookie in result.cookies
    )


async def _capture_origins(
    client: Client,
    origins: set[str],
) -> tuple[BrowserOriginState, ...]:
    """Read the localStorage of every origin we know about.

    CDP cannot list the origins that hold localStorage, so they come from the
    open tabs plus whatever the caller asked for. Sorted, so two captures of
    the same browser produce the same document.
    """
    captured: list[BrowserOriginState] = []
    for origin in sorted(origins):
        try:
            async with _loaded_origin(client, origin) as session:
                result = await session.dom_storage.get_dom_storage_items(
                    storage_id=StorageId(
                        security_origin=origin,
                        is_local_storage=True,
                    )
                )
        except Exception:
            logger.warning("Could not read localStorage of %s", origin, exc_info=True)
            continue
        items = _to_storage_items(result.entries)
        if items:
            captured.append(BrowserOriginState(origin=origin, local_storage=items))
    return tuple(captured)


def _to_storage_items(entries: Iterable[Any]) -> tuple[StorageItem, ...]:
    """DOMStorage returns entries as ``[key, value]`` pairs."""
    return tuple(
        StorageItem(name=str(entry[0]), value=str(entry[1]))
        for entry in entries
        if len(entry) == 2
    )


async def _capture_tabs(
    client: Client,
    targets: Sequence[TargetInfo],
) -> tuple[tuple[BrowserTabState, ...], int]:
    tabs: list[BrowserTabState] = []
    active_tab_index = 0
    for target in targets:
        if _to_origin(target.url) is None:
            # about:blank and chrome:// tabs are not worth restoring.
            continue
        tab, visible = await _capture_tab(client, target)
        if tab is None:
            continue
        if visible:
            active_tab_index = len(tabs)
        tabs.append(tab)
    return tuple(tabs), active_tab_index


async def _capture_tab(
    client: Client,
    target: TargetInfo,
) -> tuple[BrowserTabState | None, bool]:
    """Read one tab, falling back to its url if the page cannot be evaluated."""
    try:
        async with _attached(client, target.target_id) as session:
            result = await session.runtime.evaluate(
                expression=_CAPTURE_EXPRESSION,
                return_by_value=True,
                silent=True,
            )
            captured = result.result.value
        if not isinstance(captured, dict):
            raise TypeError("Capture expression returned no value")
    except Exception:
        logger.warning(
            "Could not read tab %s, falling back to its url",
            target.target_id,
        )
        logger.debug("Tab capture failed", exc_info=True)
        return BrowserTabState(url=target.url), False
    scroll = captured.get("scroll") or {}
    tab = BrowserTabState(
        url=str(captured.get("url") or target.url),
        scroll=ScrollPosition(
            x=int(scroll.get("x", 0)),
            y=int(scroll.get("y", 0)),
        ),
        session_storage=tuple(
            StorageItem(name=str(item["name"]), value=str(item["value"]))
            for item in captured.get("session_storage") or ()
        ),
    )
    return tab, bool(captured.get("visible"))


async def _restore_authentication(client: Client, auth: AuthenticationState) -> None:
    # A mounted authentication document replaces the cookie jar. In
    # particular, an empty profile must not inherit the previous session's
    # cookies from a pooled browser process.
    await client.storage.clear_cookies()
    if auth.cookies:
        # Storage.setCookies takes the whole list; no per-cookie round trips.
        await client.storage.set_cookies(
            cookies=[_to_cookie_param(cookie) for cookie in auth.cookies]
        )
    failed = 0
    for origin in auth.origins:
        try:
            await _restore_origin(client, origin)
        except Exception:
            failed += 1
            logger.warning("Could not write localStorage of %s", origin.origin)
            logger.debug("localStorage restore failed", exc_info=True)
    if auth.origins and failed == len(auth.origins):
        raise BrowserStateFailedException("Could not write localStorage")


def _to_cookie_param(cookie: BrowserCookie) -> CookieParam:
    return CookieParam(
        name=cookie.name,
        value=cookie.value,
        domain=cookie.domain,
        path=cookie.path,
        secure=cookie.secure,
        http_only=cookie.http_only,
        same_site=cookie.same_site,  # type: ignore[arg-type]
        expires=cookie.expires,
    )


async def _restore_origin(client: Client, origin: BrowserOriginState) -> None:
    """Write an origin's localStorage through a throwaway background tab.

    DOMStorage needs a document of that origin to exist, and writing through
    the API keeps the values out of any evaluated source string.
    """
    async with _loaded_origin(client, origin.origin) as session:
        storage_id = StorageId(
            security_origin=origin.origin,
            is_local_storage=True,
        )
        await session.dom_storage.enable()
        await session.dom_storage.clear(storage_id=storage_id)
        for item in origin.local_storage:
            await session.dom_storage.set_dom_storage_item(
                storage_id=storage_id,
                key=item.name,
                value=item.value,
            )


@asynccontextmanager
async def _loaded_origin(
    client: Client,
    origin: str,
) -> AsyncIterator[CDPSession]:
    created = await client.target.create_target(url=_BLANK_URL, background=True)
    try:
        async with _attached(client, created.target_id) as session:
            await session.page.enable()
            loaded = asyncio.create_task(
                _wait_for_load(session, timeout=10),
                name=f"browser-state:origin:{created.target_id}",
            )
            try:
                await asyncio.sleep(0)
                navigation = await session.page.navigate(url=origin)
                if navigation.error_text:
                    raise BrowserStateFailedException(navigation.error_text)
                await loaded
            finally:
                loaded.cancel()
                with suppress(BaseException):
                    await loaded
            yield session
    finally:
        with suppress(Exception):
            await client.target.close_target(target_id=created.target_id)


async def _restore_tabs(
    client: Client,
    state: BrowserState,
    settings: BrowserStateSettings,
) -> None:
    target_ids = await _align_targets(client, len(state.tabs))
    results = await asyncio.gather(
        *(
            _restore_tab(client, target_id, tab, settings)
            for target_id, tab in zip(target_ids, state.tabs, strict=True)
        ),
        return_exceptions=True,
    )
    failed = [index for index, result in enumerate(results) if result is not None]
    for index in failed:
        logger.warning("Could not restore tab %s", index)
    if len(failed) == len(state.tabs):
        raise BrowserStateFailedException("Could not restore any tab")
    await _activate(client, target_ids[state.active_tab_index])


async def _align_targets(client: Client, wanted: int) -> tuple[str, ...]:
    """Reuse the open tabs, closing or creating until there are ``wanted``.

    Reusing beats closing everything: a browser without a window may quit, and
    target churn is visible in the screencast.
    """
    targets = await _page_targets(client)
    for surplus in targets[wanted:]:
        with suppress(Exception):
            await client.target.close_target(target_id=surplus.target_id)
    target_ids = [target.target_id for target in targets[:wanted]]
    while len(target_ids) < wanted:
        created = await client.target.create_target(url=_BLANK_URL, background=True)
        target_ids.append(created.target_id)
    return tuple(target_ids)


async def _restore_tab(
    client: Client,
    target_id: str,
    tab: BrowserTabState,
    settings: BrowserStateSettings,
) -> Exception | None:
    origin = _to_origin(tab.url)
    if origin is None:
        return ValueError("Tab url has no origin")
    try:
        async with _attached(client, target_id) as session:
            await session.page.enable()
            installed = await session.page.add_script_to_evaluate_on_new_document(
                source=_build_restore_script(tab, origin)
            )
            load = asyncio.create_task(
                _wait_for_load(session, settings.restore_timeout),
                name=f"browser-state:load:{target_id}",
            )
            try:
                # Give the load listener a chance to subscribe first.
                await asyncio.sleep(0)
                navigation = await session.page.navigate(
                    url=tab.url,
                    transition_type="address_bar",
                )
                if navigation.error_text:
                    return BrowserStateFailedException(navigation.error_text)
                await load
            except TimeoutError:
                # A slow page must not fail an otherwise mounted state.
                logger.warning("Tab %s did not finish loading in time", target_id)
            finally:
                load.cancel()
                with suppress(BaseException):
                    await load
                # Without this the script would run on every later load.
                with suppress(Exception):
                    await session.page.remove_script_to_evaluate_on_new_document(
                        identifier=installed.identifier
                    )
    except Exception as error:
        return error
    return None


async def _wait_for_load(session: CDPSession, timeout: float) -> None:
    async for _ in session.listen(
        PageEvent.LOAD_EVENT_FIRED,
        LoadEventFiredEvent,
        timeout=timeout,
    ):
        return


async def _activate(client: Client, target_id: str) -> None:
    try:
        await client.target.activate_target(target_id=target_id)
        async with _attached(client, target_id) as session:
            await session.page.bring_to_front()
    except Exception:
        logger.warning("Could not bring the active tab to the front", exc_info=True)


@asynccontextmanager
async def _attached(client: Client, target_id: str) -> AsyncIterator[CDPSession]:
    """Attach to a target for one operation and detach again afterwards."""
    attached = await client.target.attach_to_target(target_id=target_id, flatten=True)
    session = client.session(attached.session_id)
    try:
        yield session
    finally:
        with suppress(Exception):
            await client.target.detach_from_target(session_id=session.session_id)


_CAPTURE_EXPRESSION = """
(() => {
    let sessionStorage = [];
    try {
        sessionStorage = Array.from(
            {length: window.sessionStorage.length},
            (_, index) => {
                const name = window.sessionStorage.key(index);
                return {name, value: window.sessionStorage.getItem(name)};
            },
        ).filter((item) => item.name !== null);
    } catch (error) {}

    return {
        url: window.location.href,
        scroll: {
            x: Math.max(0, Math.round(window.scrollX)),
            y: Math.max(0, Math.round(window.scrollY)),
        },
        session_storage: sessionStorage,
        visible: document.visibilityState === "visible",
    };
})()
"""


def _build_restore_script(tab: BrowserTabState, origin: str) -> str:
    writes = "\n        ".join(
        f"window.sessionStorage.setItem({json.dumps(item.name)}, "
        f"{json.dumps(item.value)});"
        for item in tab.session_storage
    )
    return f"""
(() => {{
    if (window.location.origin !== {json.dumps(origin)}) return;
    try {{
        window.sessionStorage.clear();
        {writes}
    }} catch (error) {{}}

    const restoreScroll = () => window.requestAnimationFrame(
        () => window.requestAnimationFrame(
            () => window.scrollTo({tab.scroll.x}, {tab.scroll.y}),
        ),
    );
    if (document.readyState === "complete") {{
        restoreScroll();
    }} else {{
        window.addEventListener("load", restoreScroll, {{once: true}});
    }}
}})();
"""
