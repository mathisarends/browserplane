import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from uuid import UUID

from browser_worker.features.browser.application.exceptions import (
    BrowserAlreadyRunningException,
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.ports import BrowserProcess


@dataclass(frozen=True, slots=True)
class RunningBrowser:
    """The id the worker's browser answers to, and where its CDP endpoint is."""

    browser_id: UUID
    upstream_cdp_url: str


class BrowserService:
    """Own the worker's single browser process and its public endpoint."""

    def __init__(
        self,
        process: BrowserProcess,
    ) -> None:
        self._process = process
        self._running: RunningBrowser | None = None
        self._release_pending = False
        self._lock = asyncio.Lock()

    async def create(self, browser_id: UUID) -> UUID:
        async with self._lock:
            if self._release_pending:
                raise BrowserAlreadyRunningException
            if self._running is not None:
                if self._running.browser_id != browser_id:
                    raise BrowserAlreadyRunningException
                return self._running.browser_id
            self._running = RunningBrowser(
                browser_id=browser_id,
                upstream_cdp_url=await self._process.start(),
            )
            return browser_id

    def get(self) -> UUID:
        if self._running is None:
            raise BrowserNotFoundException
        return self._running.browser_id

    def upstream_cdp_url(self, browser_id: UUID) -> str:
        """Resolve the endpoint a CDP client addressed by the browser's id."""
        running = self._running
        if running is None or running.browser_id != browser_id:
            raise BrowserNotFoundException
        return running.upstream_cdp_url

    async def release(self) -> None:
        """Return the browser runtime to the worker's empty initial state."""
        async with self.release_scope():
            pass

    @asynccontextmanager
    async def release_scope(self) -> AsyncGenerator[None]:
        """Keep browser creation blocked throughout worker-wide cleanup."""
        async with self._lock:
            running = self._running
            # Make the browser unavailable before waiting for its process to stop.
            # Concurrent feature requests will consequently fail as unknown rather
            # than attaching to a runtime that is currently being released.
            self._running = None
            self._release_pending = self._release_pending or running is not None
            try:
                yield
            finally:
                if self._release_pending:
                    await self._process.stop()
                    self._release_pending = False
