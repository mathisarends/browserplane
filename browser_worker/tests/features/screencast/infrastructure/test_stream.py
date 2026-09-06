import asyncio
from collections.abc import AsyncGenerator

import pytest

from browser_worker.features.screencast.infrastructure import stream as stream_module
from browser_worker.features.screencast.infrastructure.settings import ScreencastOptions
from browser_worker.features.screencast.infrastructure.stream import CdpFrameStream


class _StubClient:
    def __init__(self, cdp_url: str) -> None:
        self.cdp_url = cdp_url

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None


class _StubBridge:
    """Emit one frame, then stay quiet the way an untouched page does."""

    def __init__(self, client: object, options: ScreencastOptions) -> None:
        self.requested = 0

    async def frames(self) -> AsyncGenerator[bytes]:
        yield b"first"
        await asyncio.Event().wait()

    async def request_frame(self) -> None:
        self.requested += 1


@pytest.mark.anyio
async def test_a_joining_consumer_starts_at_the_newest_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stream_module, "Client", _StubClient)
    monkeypatch.setattr(stream_module, "ActiveTabBridge", _StubBridge)
    frame_stream = CdpFrameStream(
        "ws://browser",
        ScreencastOptions(quality=80, width=1280, height=720),
    )

    async with frame_stream.subscribe() as frames:
        assert await asyncio.wait_for(anext(frames), timeout=1) == b"first"

        async with frame_stream.subscribe() as late_frames:
            assert await asyncio.wait_for(anext(late_frames), timeout=1) == b"first"

    await frame_stream.close()
