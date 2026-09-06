import asyncio
from dataclasses import dataclass

from browser_worker.features.browser.application.exceptions import (
    BrowserAlreadyRunningException,
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.ports import BrowserProcess


@dataclass(frozen=True, slots=True)
class RunningBrowser:
    """The generation and local CDP endpoint owned by this worker."""

    generation: int
    upstream_cdp_url: str


class BrowserService:
    """Own the worker's single browser process and generation fence."""

    def __init__(self, process: BrowserProcess) -> None:
        self._process = process
        self._running: RunningBrowser | None = None
        self._high_water_generation: int | None = None
        self._releasing_generation: int | None = None
        self._poisoned_generation: int | None = None
        self._process_may_be_running = False
        self._lock = asyncio.Lock()

    async def create(self, generation: int) -> None:
        async with self._lock:
            if (
                self._releasing_generation is not None
                or self._poisoned_generation is not None
            ):
                raise BrowserAlreadyRunningException
            if self._running is not None:
                if self._running.generation != generation:
                    raise BrowserAlreadyRunningException
                return
            if (
                self._high_water_generation is not None
                and generation <= self._high_water_generation
            ):
                raise BrowserAlreadyRunningException

            upstream_cdp_url = await self._process.start()
            self._running = RunningBrowser(
                generation=generation,
                upstream_cdp_url=upstream_cdp_url,
            )
            self._process_may_be_running = True
            self._high_water_generation = generation

    def inspect(self) -> RunningBrowser:
        if self._running is None:
            raise BrowserNotFoundException
        return self._running

    def upstream_cdp_url(self) -> str:
        """Return the endpoint of the browser currently owned by this worker."""
        browser = self.inspect()
        return browser.upstream_cdp_url

    async def prepare_release(self, generation: int) -> bool:
        """Fence the runtime and report whether physical cleanup is required."""
        async with self._lock:
            if self._releasing_generation is not None:
                if self._releasing_generation != generation:
                    raise BrowserAlreadyRunningException
                return True

            running = self._running
            if running is not None:
                if running.generation != generation:
                    raise BrowserAlreadyRunningException
                self._running = None
                self._releasing_generation = generation
                return True

            if self._poisoned_generation is not None:
                if self._poisoned_generation != generation:
                    raise BrowserAlreadyRunningException
                self._releasing_generation = generation
                return True

            if self._high_water_generation == generation:
                return False
            raise BrowserAlreadyRunningException

    async def stop_process(self) -> None:
        """Stop Chromium without changing the logical release state."""
        await self._process.stop()
        self._process_may_be_running = False

    async def finish_release(self, generation: int, *, succeeded: bool) -> None:
        async with self._lock:
            if self._releasing_generation != generation:
                raise BrowserAlreadyRunningException
            self._releasing_generation = None
            if succeeded:
                self._poisoned_generation = None
                self._high_water_generation = generation
            else:
                self._poisoned_generation = generation

    async def release(self) -> None:
        """Best-effort application shutdown independent of control-plane fencing."""
        async with self._lock:
            self._running = None
            self._releasing_generation = None
            self._poisoned_generation = None
        if self._process_may_be_running:
            await self.stop_process()
