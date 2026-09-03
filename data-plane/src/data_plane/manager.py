import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from data_plane.chrome_process import ChromeProcess
from data_plane.settings import DataPlaneSettings


@dataclass(frozen=True, slots=True)
class BrowserResource:
    id: str
    state: str
    cdp_url: str


@dataclass(slots=True)
class _ManagedBrowser:
    descriptor: BrowserResource
    process: ChromeProcess
    upstream_cdp_url: str


class BrowserNotFoundError(LookupError):
    pass


class CapacityExceededError(RuntimeError):
    pass


class BrowserManager:
    def __init__(
        self,
        settings: DataPlaneSettings,
        process_factory: Callable[[DataPlaneSettings], ChromeProcess] = ChromeProcess,
    ) -> None:
        self._settings = settings
        self._process_factory = process_factory
        self._browsers: dict[str, _ManagedBrowser] = {}
        self._lock = asyncio.Lock()

    async def create(self, browser_id: str) -> BrowserResource:
        async with self._lock:
            existing = self._browsers.get(browser_id)
            if existing is not None:
                return existing.descriptor
            if len(self._browsers) >= self._settings.capacity:
                raise CapacityExceededError
            process = self._process_factory(self._settings)
            upstream_cdp_url = await process.start()
            descriptor = BrowserResource(
                id=browser_id,
                state="ready",
                cdp_url=(
                    f"{self._settings.public_base_url.rstrip('/')}"
                    f"/api/v1/browsers/{browser_id}/cdp"
                ),
            )
            self._browsers[browser_id] = _ManagedBrowser(
                descriptor=descriptor,
                process=process,
                upstream_cdp_url=upstream_cdp_url,
            )
            return descriptor

    def inspect(self, browser_id: str) -> BrowserResource:
        return self._get(browser_id).descriptor

    def upstream_cdp_url(self, browser_id: str) -> str:
        return self._get(browser_id).upstream_cdp_url

    async def destroy(self, browser_id: str) -> None:
        async with self._lock:
            managed = self._browsers.pop(browser_id, None)
            if managed is not None:
                await managed.process.stop()

    def capacity(self) -> tuple[int, int]:
        used = len(self._browsers)
        return self._settings.capacity, self._settings.capacity - used

    async def close(self) -> None:
        for browser_id in list(self._browsers):
            await self.destroy(browser_id)

    def _get(self, browser_id: str) -> _ManagedBrowser:
        try:
            return self._browsers[browser_id]
        except KeyError as error:
            raise BrowserNotFoundError(browser_id) from error
