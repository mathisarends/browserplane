import asyncio
import base64
import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable, Iterable, Sequence
from contextlib import asynccontextmanager, suppress
from functools import partial
from typing import Any
from urllib.parse import urlsplit

from cdpify import CDPSession, Client
from cdpify.domains.domstorage.types import StorageId
from cdpify.domains.fetch.events import FetchEvent, RequestPausedEvent
from cdpify.domains.fetch.types import HeaderEntry, RequestPattern
from cdpify.domains.network.types import CookieParam, CookiePartitionKey
from cdpify.domains.page.events import LoadEventFiredEvent, PageEvent
from cdpify.domains.runtime.types import CallArgument
from cdpify.domains.target.types import TargetInfo

from browser_worker.features.state.application.exceptions import (
    BrowserStateFailedException,
)
from browser_worker.features.state.application.models import (
    AuthenticationState,
    BrowserCookie,
    BrowserState,
    BrowserTabState,
    IndexedDbDatabase,
    IndexedDbIndex,
    IndexedDbObjectStore,
    IndexedDbRecord,
    OriginIndexedDb,
    OriginLocalStorage,
    ScrollPosition,
    StorageItem,
)
from browser_worker.features.state.application.models import (
    CookiePartitionKey as StateCookiePartitionKey,
)
from browser_worker.features.state.application.ports import BrowserStateStore
from browser_worker.features.state.infrastructure.settings import (
    BrowserStateSettings,
)

logger = logging.getLogger(__name__)

_WEB_SCHEMES = frozenset({"http", "https"})
_BLANK_URL = "about:blank"
_EMPTY_DOCUMENT = base64.b64encode(b"<!doctype html><title>storage</title>").decode()


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
    cookies = await _capture_cookies(client)
    origins = _origins_of(targets) | _origins_of_cookies(cookies) | set(extra_origins)
    local_storage, indexed_db = await asyncio.gather(
        _capture_local_storage(client, origins),
        _capture_indexed_db(client, origins),
    )
    return AuthenticationState(
        cookies=cookies,
        local_storage=local_storage,
        indexed_db=indexed_db,
    )


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


def _origins_of_cookies(cookies: Iterable[BrowserCookie]) -> set[str]:
    origins: set[str] = set()
    for cookie in cookies:
        host = cookie.domain.removeprefix(".")
        if not host:
            continue
        scheme = "http" if cookie.source_scheme == "NonSecure" else "https"
        port = cookie.source_port
        default_port = 80 if scheme == "http" else 443
        authority = (
            f"{host}:{port}" if port and port > 0 and port != default_port else host
        )
        origins.add(f"{scheme}://{authority}")
    return origins


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
            priority=cookie.priority,
            source_scheme=cookie.source_scheme,
            source_port=cookie.source_port,
            partition_key=(
                StateCookiePartitionKey(
                    top_level_site=cookie.partition_key.top_level_site,
                    has_cross_site_ancestor=(
                        cookie.partition_key.has_cross_site_ancestor
                    ),
                )
                if cookie.partition_key
                else None
            ),
        )
        for cookie in result.cookies
    )


async def _capture_local_storage(
    client: Client,
    origins: set[str],
) -> tuple[OriginLocalStorage, ...]:
    """Read the localStorage of every origin we know about.

    CDP cannot list the origins that hold localStorage, so they come from the
    open tabs plus whatever the caller asked for. Sorted, so two captures of
    the same browser produce the same document.
    """
    captured: list[OriginLocalStorage] = []
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
        captured.append(OriginLocalStorage(origin=origin, local_storage=items))
    return tuple(captured)


async def _capture_indexed_db(
    client: Client,
    origins: set[str],
) -> tuple[OriginIndexedDb, ...]:
    captured: list[OriginIndexedDb] = []
    for origin in sorted(origins):
        try:
            async with _loaded_origin(client, origin) as session:
                result = await session.runtime.evaluate(
                    expression=_CAPTURE_INDEXED_DB_EXPRESSION,
                    await_promise=True,
                    return_by_value=True,
                    silent=True,
                )
                raw = result.result.value
                if not isinstance(raw, list):
                    raise TypeError("IndexedDB capture returned no value")
                databases = tuple(_indexed_db_database(item) for item in raw)
        except Exception:
            logger.warning("Could not read IndexedDB of %s", origin, exc_info=True)
            continue
        captured.append(OriginIndexedDb(origin=origin, databases=databases))
    return tuple(captured)


def _indexed_db_database(value: Any) -> IndexedDbDatabase:
    return IndexedDbDatabase(
        name=str(value["name"]),
        version=int(value["version"]),
        object_stores=tuple(
            IndexedDbObjectStore(
                name=str(store["name"]),
                key_path=_indexed_db_key_path(store.get("keyPath")),
                auto_increment=bool(store.get("autoIncrement")),
                indexes=tuple(
                    IndexedDbIndex(
                        name=str(index["name"]),
                        key_path=_indexed_db_key_path(index.get("keyPath")),
                        unique=bool(index.get("unique")),
                        multi_entry=bool(index.get("multiEntry")),
                    )
                    for index in store.get("indexes", ())
                ),
                records=tuple(
                    IndexedDbRecord(key=record["key"], value=record["value"])
                    for record in store.get("records", ())
                ),
            )
            for store in value.get("objectStores", ())
        ),
    )


def _indexed_db_key_path(value: Any) -> str | tuple[str, ...] | None:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return str(value) if value is not None else None


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
    for origin in auth.local_storage:
        try:
            await _restore_origin(client, origin)
        except Exception:
            failed += 1
            logger.warning("Could not write localStorage of %s", origin.origin)
            logger.debug("localStorage restore failed", exc_info=True)
    for origin in auth.indexed_db:
        try:
            await _restore_indexed_db(client, origin)
        except Exception:
            failed += 1
            logger.warning("Could not write IndexedDB of %s", origin.origin)
            logger.debug("IndexedDB restore failed", exc_info=True)
    origin_count = len(auth.local_storage) + len(auth.indexed_db)
    if origin_count and failed == origin_count:
        raise BrowserStateFailedException("Could not write origin storage")


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
        priority=cookie.priority,  # type: ignore[arg-type]
        source_scheme=cookie.source_scheme,  # type: ignore[arg-type]
        source_port=cookie.source_port,
        partition_key=(
            CookiePartitionKey(
                top_level_site=cookie.partition_key.top_level_site,
                has_cross_site_ancestor=cookie.partition_key.has_cross_site_ancestor,
            )
            if cookie.partition_key
            else None
        ),
    )


async def _restore_origin(client: Client, origin: OriginLocalStorage) -> None:
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


async def _restore_indexed_db(client: Client, origin: OriginIndexedDb) -> None:
    """Replace an origin's IndexedDB databases from a portable snapshot."""
    payload = {
        "databases": [
            {
                "name": database.name,
                "version": database.version,
                "objectStores": [
                    {
                        "name": store.name,
                        "keyPath": _key_path_value(store.key_path),
                        "autoIncrement": store.auto_increment,
                        "indexes": [
                            {
                                "name": index.name,
                                "keyPath": _key_path_value(index.key_path),
                                "unique": index.unique,
                                "multiEntry": index.multi_entry,
                            }
                            for index in store.indexes
                        ],
                        "records": [
                            {"key": record.key, "value": record.value}
                            for record in store.records
                        ],
                    }
                    for store in database.object_stores
                ],
            }
            for database in origin.databases
        ]
    }
    async with _loaded_origin(client, origin.origin) as session:
        global_object = await session.runtime.evaluate(expression="globalThis")
        object_id = global_object.result.object_id
        if object_id is None:
            raise TypeError("Could not address the origin execution context")
        result = await session.runtime.call_function_on(
            object_id=object_id,
            function_declaration=_RESTORE_INDEXED_DB_FUNCTION,
            arguments=[CallArgument(value=payload)],
            await_promise=True,
            return_by_value=True,
            silent=True,
        )
        if result.exception_details is not None:
            raise BrowserStateFailedException("IndexedDB restore script failed")


def _key_path_value(value: str | tuple[str, ...] | None) -> str | list[str] | None:
    return list(value) if isinstance(value, tuple) else value


@asynccontextmanager
async def _loaded_origin(
    client: Client,
    origin: str,
) -> AsyncGenerator[CDPSession]:
    created = await client.target.create_target(url=_BLANK_URL, background=True)
    try:
        async with _attached(client, created.target_id) as session:
            await session.page.enable()
            await session.fetch.enable(
                patterns=[RequestPattern(resource_type="Document")]
            )
            document = asyncio.create_task(
                _fulfill_empty_document(session, timeout=10),
                name=f"browser-state:document:{created.target_id}",
            )
            loaded = asyncio.create_task(
                _wait_for_load(session, timeout=10),
                name=f"browser-state:origin:{created.target_id}",
            )
            try:
                await asyncio.sleep(0)
                navigation = await session.page.navigate(url=origin)
                if navigation.error_text:
                    raise BrowserStateFailedException(navigation.error_text)
                await document
                await loaded
            finally:
                document.cancel()
                loaded.cancel()
                with suppress(BaseException):
                    await document
                with suppress(BaseException):
                    await loaded
            yield session
    finally:
        with suppress(Exception):
            await client.target.close_target(target_id=created.target_id)


async def _fulfill_empty_document(session: CDPSession, timeout: float) -> None:
    """Create an inert document at an origin without executing that site's app."""
    async for event in session.listen(
        FetchEvent.REQUEST_PAUSED,
        RequestPausedEvent,
        timeout=timeout,
    ):
        await session.fetch.fulfill_request(
            request_id=event.request_id,
            response_code=200,
            response_headers=[
                HeaderEntry(name="Content-Type", value="text/html; charset=utf-8")
            ],
            body=_EMPTY_DOCUMENT,
        )
        return


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
async def _attached(client: Client, target_id: str) -> AsyncGenerator[CDPSession]:
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


_CAPTURE_INDEXED_DB_EXPRESSION = r"""
(async () => {
    const request = (value) => new Promise((resolve, reject) => {
        value.onsuccess = () => resolve(value.result);
        value.onerror = () => reject(value.error);
    });
    const bytes = (value) => {
        let binary = "";
        for (const byte of new Uint8Array(value)) binary += String.fromCharCode(byte);
        return btoa(binary);
    };
    const seen = new Map();
    let nextId = 1;
    const encode = async (value) => {
        if (value === undefined) return {$type: "undefined"};
        if (typeof value === "bigint") return {$type: "bigint", value: String(value)};
        if (typeof value === "number" && !Number.isFinite(value)) {
            return {$type: "number", value: String(value)};
        }
        if (value === null || typeof value !== "object") return value;
        if (seen.has(value)) return {$ref: seen.get(value)};
        const id = nextId++;
        seen.set(value, id);
        if (value instanceof Date) {
            return {$id: id, $type: "date", value: value.getTime()};
        }
        if (value instanceof RegExp) {
            return {$id: id, $type: "regexp", source: value.source, flags: value.flags};
        }
        if (value instanceof ArrayBuffer) {
            return {$id: id, $type: "arrayBuffer", value: bytes(value)};
        }
        if (ArrayBuffer.isView(value)) {
            const buffer = value.buffer.slice(
                value.byteOffset, value.byteOffset + value.byteLength,
            );
            return {
                $id: id, $type: "view", name: value.constructor.name,
                value: bytes(buffer),
            };
        }
        if (value instanceof Blob) {
            return {
                $id: id,
                $type: "blob",
                mimeType: value.type,
                value: bytes(await value.arrayBuffer()),
            };
        }
        if (value instanceof Map) {
            const entries = [];
            for (const [key, item] of value) {
                entries.push([await encode(key), await encode(item)]);
            }
            return {$id: id, $type: "map", value: entries};
        }
        if (value instanceof Set) {
            const items = [];
            for (const item of value) items.push(await encode(item));
            return {$id: id, $type: "set", value: items};
        }
        if (Array.isArray(value)) {
            const items = await Promise.all(value.map(encode));
            return {$id: id, $type: "array", value: items};
        }
        const entries = [];
        for (const key of Object.keys(value)) {
            entries.push([key, await encode(value[key])]);
        }
        return {$id: id, $type: "object", value: entries};
    };

    if (!indexedDB.databases) throw new Error("IndexedDB enumeration is unavailable");
    const databases = [];
    for (const info of await indexedDB.databases()) {
        if (!info.name) continue;
        const db = await request(indexedDB.open(info.name));
        try {
            const names = Array.from(db.objectStoreNames);
            const transaction = names.length ? db.transaction(names, "readonly") : null;
            const objectStores = [];
            for (const name of names) {
                const store = transaction.objectStore(name);
                const [keys, values] = await Promise.all([
                    request(store.getAllKeys()), request(store.getAll()),
                ]);
                const records = [];
                for (let index = 0; index < values.length; index++) {
                    records.push({
                        key: await encode(keys[index]),
                        value: await encode(values[index]),
                    });
                }
                objectStores.push({
                    name,
                    keyPath: store.keyPath,
                    autoIncrement: store.autoIncrement,
                    indexes: Array.from(store.indexNames, (indexName) => {
                        const item = store.index(indexName);
                        return {
                            name: item.name,
                            keyPath: item.keyPath,
                            unique: item.unique,
                            multiEntry: item.multiEntry,
                        };
                    }),
                    records,
                });
            }
            databases.push({name: db.name, version: db.version, objectStores});
        } finally {
            db.close();
        }
    }
    return databases;
})()
"""


_RESTORE_INDEXED_DB_FUNCTION = r"""
async function(payload) {
    const request = (value) => new Promise((resolve, reject) => {
        value.onsuccess = () => resolve(value.result);
        value.onerror = () => reject(value.error);
        value.onblocked = () => reject(new Error("IndexedDB request was blocked"));
    });
    const transaction = (value) => new Promise((resolve, reject) => {
        value.oncomplete = () => resolve();
        value.onerror = () => reject(value.error);
        value.onabort = () => reject(
            value.error || new Error("IndexedDB transaction aborted"),
        );
    });
    const binary = (value) => {
        const decoded = atob(value);
        const bytes = new Uint8Array(decoded.length);
        for (let index = 0; index < decoded.length; index++) {
            bytes[index] = decoded.charCodeAt(index);
        }
        return bytes;
    };
    const references = new Map();
    const decode = (value) => {
        if (value === null || typeof value !== "object") return value;
        if ("$ref" in value) return references.get(value.$ref);
        if (!("$type" in value)) return value;
        if (value.$type === "undefined") return undefined;
        if (value.$type === "bigint") return BigInt(value.value);
        if (value.$type === "number") return Number(value.value);
        if (value.$type === "date") {
            const result = new Date(value.value);
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "regexp") {
            const result = new RegExp(value.source, value.flags);
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "arrayBuffer") {
            const result = binary(value.value).buffer;
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "view") {
            const buffer = binary(value.value).buffer;
            const constructor = globalThis[value.name];
            const result = value.name === "DataView"
                ? new DataView(buffer)
                : new constructor(buffer);
            references.set(value.$id, result);
            return result;
        }
        if (value.$type === "blob") {
            const result = new Blob([binary(value.value)], {type: value.mimeType});
            references.set(value.$id, result); return result;
        }
        let result;
        if (value.$type === "array") result = [];
        else if (value.$type === "map") result = new Map();
        else if (value.$type === "set") result = new Set();
        else result = {};
        references.set(value.$id, result);
        if (value.$type === "array") {
            value.value.forEach((item) => result.push(decode(item)));
        } else if (value.$type === "map") {
            value.value.forEach(
                ([key, item]) => result.set(decode(key), decode(item)),
            );
        } else if (value.$type === "set") {
            value.value.forEach((item) => result.add(decode(item)));
        } else {
            value.value.forEach(([key, item]) => result[key] = decode(item));
        }
        return result;
    };

    if (indexedDB.databases) {
        for (const info of await indexedDB.databases()) {
            if (info.name) await request(indexedDB.deleteDatabase(info.name));
        }
    }
    for (const database of payload.databases) {
        const opening = indexedDB.open(database.name, database.version);
        opening.onupgradeneeded = () => {
            const db = opening.result;
            for (const definition of database.objectStores) {
                const store = db.createObjectStore(definition.name, {
                    keyPath: definition.keyPath,
                    autoIncrement: definition.autoIncrement,
                });
                for (const index of definition.indexes) {
                    store.createIndex(index.name, index.keyPath, {
                        unique: index.unique,
                        multiEntry: index.multiEntry,
                    });
                }
            }
        };
        const db = await request(opening);
        try {
            const names = database.objectStores.map((store) => store.name);
            if (!names.length) continue;
            const writing = db.transaction(names, "readwrite");
            for (const definition of database.objectStores) {
                const store = writing.objectStore(definition.name);
                for (const record of definition.records) {
                    const value = decode(record.value);
                    if (definition.keyPath === null) {
                        store.put(value, decode(record.key));
                    }
                    else store.put(value);
                }
            }
            await transaction(writing);
        } finally {
            db.close();
        }
    }
    return true;
}
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
