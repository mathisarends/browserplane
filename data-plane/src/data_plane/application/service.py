import asyncio
from collections.abc import Callable

from data_plane.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
)
from data_plane.application.models import Browser, BrowserState, Capacity
from data_plane.application.ports import BrowserProcess
from data_plane.settings import DataPlaneSettings

ProcessFactory = Callable[[DataPlaneSettings], BrowserProcess]


class _ManagedBrowser:
    __slots__ = ("browser", "process", "upstream_cdp_url")

    def __init__(
        self, browser: Browser, process: BrowserProcess, upstream_cdp_url: str
    ) -> None:
        self.browser = browser
        self.process = process
        self.upstream_cdp_url = upstream_cdp_url


class BrowserService:
    """Own the worker's browser processes and their public endpoints."""

    def __init__(
        self,
        settings: DataPlaneSettings,
        process_factory: ProcessFactory,
    ) -> None:
        self._settings = settings
        self._process_factory = process_factory
        self._browsers: dict[str, _ManagedBrowser] = {}
        self._lock = asyncio.Lock()

    async def create(self, browser_id: str) -> Browser:
        async with self._lock:
            existing = self._browsers.get(browser_id)
            if existing is not None:
                return existing.browser
            if len(self._browsers) >= self._settings.capacity:
                raise BrowserCapacityExhaustedException
            process = self._process_factory(self._settings)
            upstream_cdp_url = await process.start()
            browser = Browser(
                id=browser_id,
                state=BrowserState.READY,
                cdp_url=self._public_cdp_url(browser_id),
            )
            self._browsers[browser_id] = _ManagedBrowser(
                browser=browser,
                process=process,
                upstream_cdp_url=upstream_cdp_url,
            )
            return browser

    def get(self, browser_id: str) -> Browser:
        return self._managed(browser_id).browser

    def upstream_cdp_url(self, browser_id: str) -> str:
        return self._managed(browser_id).upstream_cdp_url

    async def destroy(self, browser_id: str) -> None:
        async with self._lock:
            managed = self._browsers.pop(browser_id, None)
            if managed is not None:
                await managed.process.stop()

    def capacity(self) -> Capacity:
        total = self._settings.capacity
        return Capacity(total=total, available=total - len(self._browsers))

    async def close(self) -> None:
        for browser_id in list(self._browsers):
            await self.destroy(browser_id)

    def _managed(self, browser_id: str) -> _ManagedBrowser:
        managed = self._browsers.get(browser_id)
        if managed is None:
            raise BrowserNotFoundException
        return managed

    def _public_cdp_url(self, browser_id: str) -> str:
        base = self._settings.public_base_url.rstrip("/")
        return f"{base}/api/v1/browsers/{browser_id}/cdp"
