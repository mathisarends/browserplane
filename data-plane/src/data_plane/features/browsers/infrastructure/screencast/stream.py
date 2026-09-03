import asyncio
import logging
from collections import deque
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass

from cdpify import Client

from data_plane.features.browsers.infrastructure.screencast.event_bridge import (
    ActiveTabBridge,
)
from data_plane.features.browsers.infrastructure.screencast.models import (
    ActiveTabChanged,
    ActiveTabFrame,
    PageUpdate,
    ScreencastOptions,
)
from data_plane.features.browsers.infrastructure.screencast.tasks import (
    cancel_and_wait,
)

logger = logging.getLogger(__name__)


class ScreencastStoppedException(Exception):
    """The browser stopped delivering updates about its active tab."""


@dataclass(frozen=True, slots=True)
class Subscription:
    """One consumer's view of the browser: its updates and the CDP connection."""

    client: Client
    updates: AsyncGenerator[PageUpdate]


class ActiveTabStream:
    """Publish one browser's active tab to every consumer over one connection.

    Chromium reports page visibility only while a page is being screencast, so
    the browser is screencast once and every consumer subscribes to the same
    updates: live viewers read the frames, the recorder reads the tab changes.
    The connection exists while at least one consumer is subscribed.
    """

    def __init__(self, cdp_url: str, options: ScreencastOptions) -> None:
        self._cdp_url = cdp_url
        self._options = options
        self._client: Client | None = None
        self._publisher: asyncio.Task[None] | None = None
        self._subscribers: set[_Subscriber] = set()
        self._active: ActiveTabChanged | None = None
        self._lock = asyncio.Lock()

    @property
    def cdp_url(self) -> str:
        return self._cdp_url

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[Subscription]:
        """Join the browser's updates, starting it for the first consumer."""
        client, subscriber = await self._join()
        updates = subscriber.updates()
        try:
            yield Subscription(client=client, updates=updates)
        finally:
            with suppress(Exception):
                await updates.aclose()
            await self._leave(subscriber)

    async def _join(self) -> tuple[Client, _Subscriber]:
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
            if self._active is not None:
                # The active tab is state, not an event: a consumer that joins
                # between two tab switches still has to learn where it stands.
                subscriber.publish(self._active)
            self._subscribers.add(subscriber)
            return self._client, subscriber

    async def _leave(self, subscriber: _Subscriber) -> None:
        async with self._lock:
            self._subscribers.discard(subscriber)
            if self._subscribers:
                return
            publisher, self._publisher = self._publisher, None
            client, self._client = self._client, None
            self._active = None
            if publisher is not None:
                await cancel_and_wait(publisher)
            if client is not None:
                with suppress(Exception):
                    await client.disconnect()

    async def _publish(self, client: Client) -> None:
        bridge = ActiveTabBridge(client, self._options)
        error: Exception = ScreencastStoppedException("Screencast publisher stopped")
        try:
            async for update in bridge.updates():
                if isinstance(update, ActiveTabChanged):
                    self._active = update
                for subscriber in tuple(self._subscribers):
                    subscriber.publish(update)
        except asyncio.CancelledError:
            raise
        except Exception as publisher_error:
            logger.debug("Active tab stream ended", exc_info=True)
            error = publisher_error
        for subscriber in tuple(self._subscribers):
            subscriber.fail(error)


class _Subscriber:
    """A mailbox that keeps every tab change but only the newest frame."""

    def __init__(self) -> None:
        self._changes: deque[ActiveTabChanged] = deque()
        self._frame: ActiveTabFrame | None = None
        self._error: Exception | None = None
        self._ready = asyncio.Event()

    def publish(self, update: PageUpdate) -> None:
        if isinstance(update, ActiveTabFrame):
            self._frame = update
        else:
            self._changes.append(update)
        self._ready.set()

    def fail(self, error: Exception) -> None:
        self._error = error
        self._ready.set()

    async def updates(self) -> AsyncGenerator[PageUpdate]:
        """Yield pending updates, dropping frames a slow consumer missed."""
        while True:
            await self._ready.wait()
            self._ready.clear()
            while self._changes:
                yield self._changes.popleft()
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
