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

_FRAME_HEADER = struct.Struct("!4sBHHHHI")
_PATCH_HEADER = struct.Struct("!HHHHI")


@pytest.mark.asyncio
async def test_stream_runs_the_encoder_worker() -> None:
    frame = Image.new("RGB", (256, 128), "white")
    stream = DirtyRectangleJpegStream(
        FakeFrameStream(_png(frame)),
        _settings(),
    )

    async with stream.subscribe() as updates:
        packets = [packet async for packet in updates]

    assert [_patches(packet) for packet in packets] == [[(0, 0, 256, 128)]]


def test_encoder_sends_a_full_frame_then_only_changed_tiles() -> None:
    first = Image.new("RGB", (256, 128), "white")
    second = first.copy()
    ImageDraw.Draw(second).rectangle((0, 0, 10, 10), fill="black")

    previous, first_packet, _ = encode_update(_png(first), None, _settings())
    previous, second_packet, _ = encode_update(_png(second), previous, _settings())
    _, unchanged_packet, _ = encode_update(_png(second), previous, _settings())

    assert first_packet is not None
    assert second_packet is not None
    assert _patches(first_packet) == [(0, 0, 256, 128)]
    assert _patches(second_packet) == [(0, 0, 64, 64)]
    assert unchanged_packet is None


def test_encoder_merges_neighbouring_tiles_but_keeps_islands_apart() -> None:
    first = Image.new("RGB", (256, 128), "white")
    second = first.copy()
    drawing = ImageDraw.Draw(second)
    drawing.rectangle((0, 0, 127, 10), fill="black")
    drawing.rectangle((200, 100, 210, 110), fill="black")

    previous, _, _ = encode_update(_png(first), None, _settings())
    _, packet, _ = encode_update(_png(second), previous, _settings())

    assert packet is not None
    assert _patches(packet) == [(0, 0, 128, 64), (192, 64, 64, 64)]


def _settings() -> DirtyRectangleSettings:
    return DirtyRectangleSettings(tile_width=64, tile_height=64, jpeg_quality=80)


def _png(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _patches(packet: bytes) -> list[tuple[int, int, int, int]]:
    magic, version, width, height, tile_width, tile_height, count = (
        _FRAME_HEADER.unpack_from(packet)
    )
    assert (magic, version, width, height) == (b"DRJP", 2, 256, 128)
    assert (tile_width, tile_height) == (64, 64)

    patches = []
    offset = _FRAME_HEADER.size
    for _ in range(count):
        x, y, patch_width, patch_height, length = _PATCH_HEADER.unpack_from(
            packet, offset
        )
        patches.append((x, y, patch_width, patch_height))
        offset += _PATCH_HEADER.size + length
    assert offset == len(packet)
    return patches
