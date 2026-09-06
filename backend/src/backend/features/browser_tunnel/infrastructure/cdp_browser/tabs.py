from collections.abc import Awaitable, Callable

from cdpify import Client
from cdpify.domains.target.types import TargetInfo

from backend.features.browser_tunnel.application import (
    BrowserTab,
    BrowserTabs,
)


class CdpTabs(BrowserTabs):
    def __init__(
        self,
        client: Callable[[], Client],
        active_target_id: Callable[[], str | None],
        select: Callable[[str], Awaitable[None]],
        close: Callable[[str], Awaitable[None]],
    ) -> None:
        self._client = client
        self._active_target_id = active_target_id
        self._select = select
        self._close = close
        self._tab_order: list[str] = []

    async def list(self) -> list[BrowserTab]:
        pages = await self.page_targets()
        pages_by_id = {page.target_id: page for page in pages}
        self._tab_order = [
            tab_id for tab_id in self._tab_order if tab_id in pages_by_id
        ]

        new_tab_ids = [
            page.target_id for page in pages if page.target_id not in self._tab_order
        ]
        active_tab_id = self._active_target_id()
        insert_at = (
            self._tab_order.index(active_tab_id) + 1
            if active_tab_id in self._tab_order
            else len(self._tab_order)
        )
        self._tab_order[insert_at:insert_at] = new_tab_ids

        return [
            BrowserTab(
                id=page.target_id,
                title=page.title,
                url=page.url,
                active=page.target_id == self._active_target_id(),
            )
            for tab_id in self._tab_order
            if (page := pages_by_id.get(tab_id)) is not None
        ]

    async def create(self, url: str) -> list[BrowserTab]:
        await self.list()
        active_tab_id = self._active_target_id()
        created = await self._client().target.create_target(url=url)
        insert_at = (
            self._tab_order.index(active_tab_id) + 1
            if active_tab_id in self._tab_order
            else len(self._tab_order)
        )
        self._tab_order.insert(insert_at, created.target_id)
        await self._select(created.target_id)
        return await self.list()

    async def activate(self, tab_id: str) -> list[BrowserTab]:
        await self._select(tab_id)
        return await self.list()

    async def close(self, tab_id: str) -> list[BrowserTab]:
        await self._close(tab_id)
        return await self.list()

    async def page_targets(self) -> list[TargetInfo]:
        targets = await self._client().target.get_targets()
        return [target for target in targets.target_infos if target.type == "page"]
