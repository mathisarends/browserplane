import asyncio
from collections.abc import AsyncIterator
from contextlib import ExitStack, suppress

from cdpify import Client
from cdpify.domains.browser.types import PermissionDescriptor
from cdpify.exceptions import CDPCommandException

from backend.features.browser_tunnel.application import (
    Browser,
    BrowserEvent,
    BrowserTabNotFoundError,
    CursorChanged,
    TabsChanged,
    TargetDetached,
)
from backend.features.browser_tunnel.infrastructure.cdp_browser.active_page import (
    ActiveClipboard,
    ActiveInput,
    ActiveNavigation,
    ActivePage,
)
from backend.features.browser_tunnel.infrastructure.cdp_browser.page import CdpPage
from backend.features.browser_tunnel.infrastructure.cdp_browser.tabs import CdpTabs
from backend.features.browser_tunnel.infrastructure.events.stream import (
    BrowserEventStream,
)
from backend.features.browser_tunnel.infrastructure.settings import BrowserSettings
from backend.features.browser_tunnel.infrastructure.target_event_bridge import (
    TargetEventBridge,
)


class CdpBrowser(Browser):
    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._client: Client | None = None
        self._active = ActivePage()
        self._events = BrowserEventStream()
        self._navigation = ActiveNavigation(self._active)
        self._input = ActiveInput(self._active)
        self._clipboard = ActiveClipboard(self._active)
        self._tabs = CdpTabs(
            self._connected_client,
            self._active_target_id,
            self._select_target,
            self._close_target,
        )
        self._targets = TargetEventBridge(
            self._events.publish,
            self._on_targets_changed,
            self._on_detached,
            self._events.close,
        )

    @property
    def navigation(self) -> ActiveNavigation:
        return self._navigation

    @property
    def input(self) -> ActiveInput:
        return self._input

    @property
    def clipboard(self) -> ActiveClipboard:
        return self._clipboard

    @property
    def tabs(self) -> CdpTabs:
        return self._tabs

    async def start(self) -> None:
        try:
            async with self._active.lock:
                if self._client is not None:
                    return
                client = Client(self._settings.cdp_url)
                self._client = client
                await client.connect()
                await self._targets.start(client)
                await client.target.set_discover_targets(discover=True)
                for permission in ("clipboard-read", "clipboard-write"):
                    await client.browser.set_permission(
                        permission=PermissionDescriptor(name=permission),
                        setting="granted",
                    )
                await self._select_any_page()
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        await self._targets.stop()
        async with self._active.lock:
            try:
                await self._release_active_page()
            finally:
                client, self._client = self._client, None
                try:
                    if client is not None:
                        await client.disconnect()
                finally:
                    self._events.close()

    async def events(self) -> AsyncIterator[BrowserEvent]:
        with ExitStack() as subscriptions:
            async with self._active.lock:
                while True:
                    revision = self._events.revision
                    snapshot = await self._snapshot()
                    if revision == self._events.revision:
                        break
                queue = subscriptions.enter_context(self._events.subscribe())
            for event in snapshot:
                yield event
            while True:
                try:
                    yield await queue.get()
                except asyncio.QueueShutDown as error:
                    raise RuntimeError("Browser event stream is unavailable") from error

    def _connected_client(self) -> Client:
        if self._client is None:
            raise RuntimeError("Browser tunnel has not been started")
        return self._client

    def _active_target_id(self) -> str | None:
        page = self._active.page
        return page.target_id if page is not None else None

    async def _select_target(self, target_id: str) -> None:
        async with self._active.lock:
            await self._switch_page(target_id)

    async def _switch_page(self, target_id: str) -> None:
        client = self._connected_client()
        if not any(
            page.target_id == target_id for page in await self._tabs.page_targets()
        ):
            raise BrowserTabNotFoundError(target_id)
        if target_id == self._active_target_id():
            return
        await self._release_active_page()
        await client.target.activate_target(target_id=target_id)
        attached = await client.target.attach_to_target(
            target_id=target_id, flatten=True
        )

        def publish(event: BrowserEvent) -> None:
            if self._active.page is page:
                self._events.publish(event)

        page = CdpPage(
            client.session(attached.session_id),
            target_id,
            self._tabs.list,
            publish,
            self._events.close,
        )
        try:
            await page.start(self._settings)
        except BaseException:
            await self._release_page(page)
            raise
        self._active.page = page
        await self._publish_snapshot()

    async def _release_active_page(self) -> None:
        page, self._active.page = self._active.page, None
        if page is not None:
            await self._release_page(page)

    async def _release_page(self, page: CdpPage) -> None:
        try:
            await page.stop()
        finally:
            with suppress(CDPCommandException):
                await self._connected_client().target.detach_from_target(
                    session_id=page.session.session_id
                )

    async def _select_any_page(self, *, exclude: str | None = None) -> None:
        pages = [
            page
            for page in await self._tabs.page_targets()
            if page.target_id != exclude
        ]
        if pages:
            await self._switch_page(pages[0].target_id)
        else:
            created = await self._connected_client().target.create_target(
                url="about:blank"
            )
            await self._switch_page(created.target_id)

    async def _close_target(self, target_id: str) -> None:
        async with self._active.lock:
            if not any(
                page.target_id == target_id for page in await self._tabs.page_targets()
            ):
                raise BrowserTabNotFoundError(target_id)
            await self._connected_client().target.close_target(target_id=target_id)
            if target_id == self._active_target_id():
                await self._select_any_page(exclude=target_id)

    async def _on_detached(self, target_id: str | None, session_id: str | None) -> None:
        async with self._active.lock:
            page = self._active.page
            if session_id is not None:
                if page is None or session_id != page.session.session_id:
                    return
                target_id = page.target_id
            self._events.publish(TargetDetached(target_id))
            if page is not None and target_id == page.target_id:
                await self._select_any_page(exclude=target_id)

    async def _on_targets_changed(self, target_id: str | None) -> None:
        async with self._active.lock:
            self._events.publish(TabsChanged(await self._tabs.list()))
            page = self._active.page
            if page is not None and target_id == page.target_id:
                navigation = await page.events.current_navigation()
                if navigation is not None:
                    self._events.publish(navigation)

    async def _snapshot(self) -> list[BrowserEvent]:
        events: list[BrowserEvent] = [TabsChanged(await self._tabs.list())]
        page = self._active.page
        if page is not None:
            navigation = await page.events.current_navigation()
            if navigation is not None:
                events.append(navigation)
            events.append(CursorChanged(page.target_id, page.cursor.cursor))
        return events

    async def _publish_snapshot(self) -> None:
        for event in await self._snapshot():
            self._events.publish(event)
