from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager

type FrameIterator = AsyncIterator[bytes]
type FrameSubscription = AbstractAsyncContextManager[FrameIterator]


class FrameStream(ABC):
    @abstractmethod
    def subscribe(self) -> FrameSubscription: ...


type FrameStreamFactory = Callable[[str], FrameStream]
