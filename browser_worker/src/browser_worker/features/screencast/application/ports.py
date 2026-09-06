from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

type FrameIterator = AsyncIterator[bytes]
type FrameSubscription = AbstractAsyncContextManager[FrameIterator]


class FrameStream(Protocol):
    """A subscribable stream of binary frame messages."""

    def subscribe(self) -> FrameSubscription: ...

    async def close(self) -> None:
        """Close the stream and all of its browser-side resources."""


type FrameStreamFactory = Callable[[str], FrameStream]
