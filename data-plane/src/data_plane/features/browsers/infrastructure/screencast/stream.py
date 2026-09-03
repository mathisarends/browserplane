import asyncio
from collections.abc import AsyncGenerator, AsyncIterator

from cdpify import Client

from data_plane.features.browsers.infrastructure.screencast.event_bridge import (
    ScreencastEventBridge,
)
from data_plane.features.browsers.infrastructure.screencast.tasks import (
    cancel_and_wait,
)


class Screencast:
    """Publish the visible Chromium tab as a latest-frame JPEG stream."""

    def __init__(
        self,
        cdp_url: str,
        *,
        quality: int,
        width: int,
        height: int,
    ) -> None:
        self._client = Client(cdp_url)
        self._quality = quality
        self._width = width
        self._height = height

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self.frames()

    async def frames(self) -> AsyncGenerator[bytes]:
        """Yield JPEG bytes, dropping stale frames when the consumer is slow."""
        frames: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
        async with self._client:
            publisher = asyncio.create_task(
                self._publish_frames(frames),
                name="screencast:publisher",
            )
            next_frame = asyncio.create_task(frames.get())
            try:
                while True:
                    done, _ = await asyncio.wait(
                        (publisher, next_frame),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if publisher in done:
                        await cancel_and_wait(next_frame)
                        await publisher
                        raise RuntimeError("Screencast publisher stopped")
                    yield next_frame.result()
                    next_frame = asyncio.create_task(frames.get())
            finally:
                await cancel_and_wait(publisher, next_frame)

    async def _publish_frames(self, frames: asyncio.Queue[bytes]) -> None:
        event_bridge = ScreencastEventBridge(
            self._client,
            quality=self._quality,
            width=self._width,
            height=self._height,
        )
        async for frame in event_bridge.frames():
            _publish_latest(frames, frame)


def _publish_latest(frames: asyncio.Queue[bytes], frame: bytes) -> None:
    if frames.full():
        frames.get_nowait()
    frames.put_nowait(frame)
