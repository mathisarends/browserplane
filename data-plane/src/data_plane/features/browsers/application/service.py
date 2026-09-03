import asyncio
from collections.abc import Callable
from uuid import UUID

from data_plane.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
)
from data_plane.features.browsers.application.models import Browser, Capacity
from data_plane.features.browsers.application.ports import BrowserProcess
from data_plane.features.browsers.application.store import BrowserStore, ManagedBrowser
from data_plane.settings import DataPlaneSettings

ProcessFactory = Callable[[DataPlaneSettings], BrowserProcess]


class BrowserService:
    """Own the worker's browser processes and their public endpoints."""

    def __init__(
        self,
        settings: DataPlaneSettings,
        process_factory: ProcessFactory,
    ) -> None:
        self._settings = settings
        self._process_factory = process_factory
        self._store = BrowserStore()
        self._lock = asyncio.Lock()

    async def create(self, browser_id: UUID) -> Browser:
        async with self._lock:
            existing = self._store.get(browser_id)
            if existing is not None:
                return existing.browser
            if len(self._store) >= self._settings.capacity:
                raise BrowserCapacityExhaustedException
            process = self._process_factory(self._settings)
            upstream_cdp_url = await process.start()
            browser = Browser(
                id=browser_id,
                cdp_url=self._public_cdp_url(browser_id),
            )
            self._store.add(
                browser_id,
                ManagedBrowser(
                    browser=browser,
                    process=process,
                    upstream_cdp_url=upstream_cdp_url,
                ),
            )
            return browser

    def get(self, browser_id: UUID) -> Browser:
        return self._managed(browser_id).browser

    def upstream_cdp_url(self, browser_id: UUID) -> str:
        return self._managed(browser_id).upstream_cdp_url

    async def destroy(self, browser_id: UUID) -> None:
        async with self._lock:
            managed = self._store.remove(browser_id)
            if managed is not None:
                await managed.process.stop()

    def capacity(self) -> Capacity:
        total = self._settings.capacity
        return Capacity(total=total, available=total - len(self._store))

    async def close(self) -> None:
        for browser_id in self._store.ids():
            await self.destroy(browser_id)

    def _managed(self, browser_id: UUID) -> ManagedBrowser:
        managed = self._store.get(browser_id)
        if managed is None:
            raise BrowserNotFoundException
        return managed

    def _public_cdp_url(self, browser_id: UUID) -> str:
        base = self._settings.public_base_url.rstrip("/")
        return f"{base}/api/v1/browsers/{browser_id}/cdp"
