import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from data_plane.features.browsers.application.exceptions import (
    BrowserAlreadyRunningException,
    BrowserNotFoundException,
)
from data_plane.features.browsers.application.models import Browser
from data_plane.features.browsers.application.ports import BrowserProcess
from data_plane.settings import DataPlaneSettings

ProcessFactory = Callable[[DataPlaneSettings], BrowserProcess]


@dataclass(frozen=True, slots=True)
class RunningBrowser:
    """A browser together with the process and endpoint backing it."""

    browser: Browser
    process: BrowserProcess
    upstream_cdp_url: str


class BrowserService:
    """Own the worker's single browser process and its public endpoint."""

    def __init__(
        self,
        settings: DataPlaneSettings,
        process_factory: ProcessFactory,
    ) -> None:
        self._settings = settings
        self._process_factory = process_factory
        self._running: RunningBrowser | None = None
        self._lock = asyncio.Lock()

    async def create(self, browser_id: UUID) -> Browser:
        async with self._lock:
            if self._running is not None:
                if self._running.browser.id != browser_id:
                    raise BrowserAlreadyRunningException
                return self._running.browser
            process = self._process_factory(self._settings)
            upstream_cdp_url = await process.start()
            browser = Browser(
                id=browser_id,
                cdp_url=self._public_cdp_url(browser_id),
            )
            self._running = RunningBrowser(
                browser=browser,
                process=process,
                upstream_cdp_url=upstream_cdp_url,
            )
            return browser

    def get(self) -> Browser:
        return self._require().browser

    def upstream_cdp_url(self, browser_id: UUID) -> str:
        """Resolve the endpoint a CDP client addressed by the browser's id."""
        running = self._require()
        if running.browser.id != browser_id:
            raise BrowserNotFoundException
        return running.upstream_cdp_url

    async def destroy(self) -> None:
        async with self._lock:
            running = self._running
            if running is None:
                return
            self._running = None
            await running.process.stop()

    async def close(self) -> None:
        await self.destroy()

    def _require(self) -> RunningBrowser:
        if self._running is None:
            raise BrowserNotFoundException
        return self._running

    def _public_cdp_url(self, browser_id: UUID) -> str:
        base = self._settings.public_base_url.rstrip("/")
        return f"{base}/api/v1/browser/{browser_id}/cdp"
