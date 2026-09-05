from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from browser_worker.features.browser.application.ports import BrowserProcess
from browser_worker.features.screencast.application.ports import FrameStream


class FakeBrowserProcess(BrowserProcess):
    """Small observable browser process used by application-service tests."""

    def __init__(self) -> None:
        self.start_count = 0
        self.stop_count = 0

    async def start(self) -> str:
        self.start_count += 1
        return "ws://chromium/devtools/browser/test"

    async def stop(self) -> None:
        self.stop_count += 1


class FakeFrameStream(FrameStream):
    """Finite frame stream for recorder and screencast service tests."""

    def __init__(self, *frames: bytes) -> None:
        self._items = frames

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[AsyncIterator[bytes]]:
        yield self._frames()

    async def _frames(self) -> AsyncIterator[bytes]:
        for frame in self._items:
            yield frame
