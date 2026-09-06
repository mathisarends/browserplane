import asyncio
from collections.abc import Callable, Generator
from contextlib import contextmanager

from backend.features.browser_tunnel.application import BrowserEvent

type PublishEvent = Callable[[BrowserEvent], None]


class BrowserEventStream:
    def __init__(self, *, maxsize: int = 16) -> None:
        if maxsize < 1:
            raise ValueError("Event queue size must be positive")
        self._maxsize = maxsize
        self._subscribers: set[asyncio.Queue[BrowserEvent]] = set()
        self.revision = 0
        self._closed = False

    @contextmanager
    def subscribe(self) -> Generator[asyncio.Queue[BrowserEvent]]:
        if self._closed:
            raise RuntimeError("Browser event stream is closed")
        queue: asyncio.Queue[BrowserEvent] = asyncio.Queue(self._maxsize)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)
            queue.shutdown(immediate=True)

    def publish(self, event: BrowserEvent) -> None:
        self.revision += 1
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                self._subscribers.discard(queue)
                queue.shutdown(immediate=True)

    def close(self) -> None:
        self._closed = True
        for queue in self._subscribers:
            queue.shutdown(immediate=True)
        self._subscribers.clear()
