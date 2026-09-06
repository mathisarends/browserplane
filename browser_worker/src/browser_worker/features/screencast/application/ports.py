from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager

type FrameIterator = AsyncIterator[bytes]
type FrameSubscription = AbstractAsyncContextManager[FrameIterator]


class FrameStream(ABC):
    @abstractmethod
    def subscribe(self) -> FrameSubscription: ...

    @abstractmethod
    async def close(self) -> None:
        """Close the stream and all of its browser-side resources."""


type FrameStreamFactory = Callable[[str], FrameStream]
