import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager, suppress

from cdpify import Client

from data_plane.features.browsers.infrastructure.screencast.event_bridge import (
    ActiveTabBridge,
)
from data_plane.features.browsers.infrastructure.screencast.models import (
    ScreencastOptions,
)
from data_plane.features.browsers.infrastructure.screencast.tasks import (
    cancel_and_wait,
)

logger = logging.getLogger(__name__)


class ScreencastStoppedException(Exception):
    """The browser stopped delivering updates about its active tab."""


class ActiveTabStream:
    """Publish raw JPEG frames from one browser's active tab.

    Chromium reports page visibility only while a page is being screencast, so
    the browser is screencast once and every consumer subscribes to the same raw
    frame stream. The connection exists while at least one consumer subscribes.
    """

    def __init__(self, cdp_url: str, options: ScreencastOptions) -> None:
        self._cdp_url = cdp_url
        self._options = options
        self._client: Client | None = None
        self._publisher: asyncio.Task[None] | None = None
        self._subscribers: set[_Subscriber] = set()
        self._lock = asyncio.Lock()

    @property
    def cdp_url(self) -> str:
        return self._cdp_url

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[AsyncGenerator[bytes]]:
        """Join the browser's raw frame stream."""
        subscriber = await self._join()
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
                self._publisher = asyncio.create_task(
                    self._publish(client),
                    name="screencast:publisher",
                )
            subscriber = _Subscriber()
            self._subscribers.add(subscriber)
            return subscriber

    async def _leave(self, subscriber: _Subscriber) -> None:
        async with self._lock:
            self._subscribers.discard(subscriber)
            if self._subscribers:
                return
            publisher, self._publisher = self._publisher, None
            client, self._client = self._client, None
            if publisher is not None:
                await cancel_and_wait(publisher)
            if client is not None:
                with suppress(Exception):
                    await client.disconnect()

    async def _publish(self, client: Client) -> None:
        bridge = ActiveTabBridge(client, self._options)
        error: Exception = ScreencastStoppedException("Screencast publisher stopped")
        try:
            async for frame in bridge.frames():
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

    def __init__(self) -> None:
        self._frame: bytes | None = None
        self._error: Exception | None = None
        self._ready = asyncio.Event()

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


class ActiveTabStreams:
    """Hand out the shared active-tab stream of the worker's browser.

    A worker owns exactly one browser at a time, so a new CDP endpoint replaces
    the previous stream; consumers of the browser that is gone end on their own.
    """

    def __init__(self, options: ScreencastOptions) -> None:
        self._options = options
        self._stream: ActiveTabStream | None = None

    def for_browser(self, cdp_url: str) -> ActiveTabStream:
        if self._stream is None or self._stream.cdp_url != cdp_url:
            self._stream = ActiveTabStream(cdp_url, self._options)
        return self._stream
