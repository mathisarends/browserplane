import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from cdpify import Client

from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.features.screencast.infrastructure.cdp import (
    ActiveTabBridge,
)
from browser_worker.features.screencast.infrastructure.settings import ScreencastOptions
from browser_worker.features.screencast.infrastructure.tasks import (
    cancel_and_wait,
)

logger = logging.getLogger(__name__)


class ScreencastStoppedException(Exception):
    """The browser stopped delivering updates about its active tab."""


class CdpFrameStream(FrameStream):
    """Publish raw JPEG frames from one browser's active tab.

    Chromium reports page visibility only while a page is being screencast, so
    the browser is screencast once and every consumer subscribes to the same raw
    frame stream. The connection exists while at least one consumer subscribes.

    Chromium only emits a frame when the page changes, so the newest frame is
    kept and replayed to consumers as they join. Without it a consumer that
    connects to a page nobody is touching would stare at nothing until the next
    repaint.
    """

    def __init__(self, cdp_url: str, options: ScreencastOptions) -> None:
        self._cdp_url = cdp_url
        self._options = options
        self._client: Client | None = None
        self._bridge: ActiveTabBridge | None = None
        self._publisher: asyncio.Task[None] | None = None
        self._subscribers: set[_Subscriber] = set()
        self._latest: bytes | None = None
        self._lock = asyncio.Lock()

    @property
    def cdp_url(self) -> str:
        return self._cdp_url

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[AsyncGenerator[bytes]]:
        """Join the browser's raw frame stream, starting at the newest frame."""
        subscriber = await self._join()
        if subscriber.waiting:
            await self._request_frame()
        frames = subscriber.frames()
        try:
            yield frames
        finally:
            with suppress(Exception):
                await frames.aclose()
            await self._leave(subscriber)

    async def _join(self) -> _Subscriber:
        async with self._lock:
            if self._client is None:
                client = Client(self._cdp_url)
                await client.connect()
                self._client = client
                self._bridge = ActiveTabBridge(client, self._options)
                self._publisher = asyncio.create_task(
                    self._publish(self._bridge),
                    name="screencast:publisher",
                )
            subscriber = _Subscriber(self._latest)
            self._subscribers.add(subscriber)
            return subscriber

    async def _leave(self, subscriber: _Subscriber) -> None:
        async with self._lock:
            self._subscribers.discard(subscriber)
            if self._subscribers:
                return
            publisher, self._publisher = self._publisher, None
            client, self._client = self._client, None
            self._bridge = None
            if publisher is not None:
                await cancel_and_wait(publisher)
            if client is not None:
                with suppress(Exception):
                    await client.disconnect()

    async def close(self) -> None:
        """Stop publishing and disconnect even while consumers are subscribed."""
        async with self._lock:
            publisher, self._publisher = self._publisher, None
            client, self._client = self._client, None
            self._bridge = None
            self._latest = None
            if publisher is not None:
                await cancel_and_wait(publisher)
            if client is not None:
                with suppress(Exception):
                    await client.disconnect()
            error = ScreencastStoppedException("Browser was released")
            for subscriber in tuple(self._subscribers):
                subscriber.fail(error)

    async def _request_frame(self) -> None:
        """Ask the browser for a frame a joining consumer could not be given.

        Only reached when no frame has ever been seen for this browser, so it
        costs one repaint per consumer that would otherwise wait indefinitely -
        never a stream of frames nobody asked for.
        """
        bridge = self._bridge
        if bridge is not None:
            await bridge.request_frame()

    async def _publish(self, bridge: ActiveTabBridge) -> None:
        error: Exception = ScreencastStoppedException("Screencast publisher stopped")
        try:
            async for frame in bridge.frames():
                self._latest = frame
                for subscriber in tuple(self._subscribers):
                    subscriber.publish(frame)
        except asyncio.CancelledError:
            raise
        except Exception as publisher_error:
            logger.debug("Active tab stream ended", exc_info=True)
            error = publisher_error
        for subscriber in tuple(self._subscribers):
            subscriber.fail(error)


class _Subscriber:
    """A mailbox that keeps only the newest frame."""

    def __init__(self, frame: bytes | None = None) -> None:
        self._frame = frame
        self._error: Exception | None = None
        self._ready = asyncio.Event()
        if frame is not None:
            self._ready.set()

    @property
    def waiting(self) -> bool:
        """Whether this mailbox is still empty and has nothing to yield yet."""
        return not self._ready.is_set()

    def publish(self, frame: bytes) -> None:
        self._frame = frame
        self._ready.set()

    def fail(self, error: Exception) -> None:
        self._error = error
        self._ready.set()

    async def frames(self) -> AsyncGenerator[bytes]:
        """Yield raw JPEG bytes, dropping frames a slow consumer missed."""
        while True:
            await self._ready.wait()
            self._ready.clear()
            frame, self._frame = self._frame, None
            if frame is not None:
                yield frame
            if self._error is not None:
                raise self._error
