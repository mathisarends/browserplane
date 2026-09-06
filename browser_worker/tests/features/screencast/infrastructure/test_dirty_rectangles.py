import io
import struct

import pytest
from PIL import Image, ImageDraw
from tests.fakes import FakeFrameStream

from browser_worker.features.screencast.infrastructure.dirty_rectangles import (
    DirtyRectangleJpegStream,
)


@pytest.mark.asyncio
async def test_stream_sends_a_full_frame_then_only_changed_tiles() -> None:
    first = Image.new("RGB", (256, 128), "white")
    second = first.copy()
    ImageDraw.Draw(second).rectangle((0, 0, 10, 10), fill="black")
    stream = DirtyRectangleJpegStream(
        FakeFrameStream(_png(first), _png(second), _png(second))
    )

    async with stream.subscribe() as updates:
        packets = [packet async for packet in updates]

    assert [_patch_count(packet) for packet in packets] == [2, 1]


def _png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _patch_count(packet: bytes) -> int:
    magic, version, width, height, count = struct.unpack_from("!4sBHHI", packet)
    assert (magic, version, width, height) == (b"DRJP", 1, 256, 128)
    return count
