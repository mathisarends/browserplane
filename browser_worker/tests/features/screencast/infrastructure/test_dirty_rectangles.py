import io
import struct

import pytest
from PIL import Image, ImageDraw
from tests.fakes import FakeFrameStream

from browser_worker.features.screencast.infrastructure.dirty_rectangles import (
    DirtyRectangleJpegStream,
    encode_update,
)
from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
)


@pytest.mark.asyncio
async def test_stream_runs_the_encoder_worker() -> None:
    frame = Image.new("RGB", (256, 128), "white")
    stream = DirtyRectangleJpegStream(
        FakeFrameStream(_png(frame)),
        _settings(),
    )

    async with stream.subscribe() as updates:
        packets = [packet async for packet in updates]

    assert [_patch_count(packet) for packet in packets] == [2]


def test_encoder_sends_a_full_frame_then_only_changed_tiles() -> None:
    first = Image.new("RGB", (256, 128), "white")
    second = first.copy()
    ImageDraw.Draw(second).rectangle((0, 0, 10, 10), fill="black")

    previous, first_packet, _ = encode_update(_png(first), None, _settings())
    previous, second_packet, _ = encode_update(_png(second), previous, _settings())
    _, unchanged_packet, _ = encode_update(_png(second), previous, _settings())

    assert first_packet is not None
    assert second_packet is not None
    assert [_patch_count(first_packet), _patch_count(second_packet)] == [2, 1]
    assert unchanged_packet is None


def _settings() -> DirtyRectangleSettings:
    return DirtyRectangleSettings(
        tile_width=128,
        tile_height=128,
        jpeg_quality=80,
    )


def _png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _patch_count(packet: bytes) -> int:
    magic, version, width, height, count = struct.unpack_from("!4sBHHI", packet)
    assert (magic, version, width, height) == (b"DRJP", 1, 256, 128)
    return count
