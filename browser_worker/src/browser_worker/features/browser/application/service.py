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
    generation: int
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

    async def create(self, browser_id: UUID, generation: int = 0) -> UUID:
        async with self._lock:
            if self._release_pending:
                raise BrowserAlreadyRunningException
            if self._running is not None:
                if (
                    self._running.browser_id != browser_id
                    or self._running.generation != generation
                ):
                    raise BrowserAlreadyRunningException
                return self._running.browser_id
            self._running = RunningBrowser(
                browser_id=browser_id,
                generation=generation,
                upstream_cdp_url=await self._process.start(),
            )
            return self._running.browser_id

    def get(self) -> UUID:
        if self._running is None:
            raise BrowserNotFoundException
        return self._running.browser_id

    def inspect(self) -> RunningBrowser:
        if self._running is None:
            raise BrowserNotFoundException
        return self._running

    def upstream_cdp_url(self) -> str:
        """Return the endpoint of the browser currently owned by this worker."""
        browser = self.inspect()
        return browser.upstream_cdp_url

    async def release(self) -> None:
        """Return the browser runtime to the worker's empty initial state."""
        async with self.release_scope():
            pass

    @asynccontextmanager
    async def release_scope(
        self,
        browser_id: UUID | None = None,
        generation: int | None = None,
    ) -> AsyncGenerator[None]:
        """Keep browser creation blocked throughout worker-wide cleanup."""
        async with self._lock:
            running = self._running
            if running is not None and (
                (browser_id is not None and running.browser_id != browser_id)
                or (generation is not None and running.generation != generation)
            ):
                raise BrowserAlreadyRunningException
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
