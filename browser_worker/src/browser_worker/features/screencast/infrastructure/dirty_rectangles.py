import asyncio
import io
import logging
import struct
import time
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from PIL import Image

from browser_worker.features.screencast.application.ports import FrameStream

logger = logging.getLogger(__name__)

# Each update is one websocket message:
#   frame header: magic, version, canvas width, canvas height, patch count
#   patch*: x, y, width, height, JPEG byte length, JPEG bytes
_FRAME_HEADER = struct.Struct("!4sBHHI")
_PATCH_HEADER = struct.Struct("!HHHHI")
_MAGIC = b"DRJP"
_VERSION = 1

type RgbFrame = npt.NDArray[np.uint8]


@dataclass(frozen=True, slots=True)
class DirtyRectangleOptions:
    tile_width: int = 128
    tile_height: int = 128
    jpeg_quality: int = 80

    def __post_init__(self) -> None:
        if self.tile_width <= 0 or self.tile_height <= 0:
            raise ValueError("Dirty rectangle tile dimensions must be positive")
        if not 0 <= self.jpeg_quality <= 100:
            raise ValueError("Dirty rectangle JPEG quality must be between 0 and 100")


class DirtyRectangleJpegStream:
    """Adapt complete image frames to packets containing changed JPEG tiles.

    Diff state belongs to a subscription, so every new consumer starts with a
    complete canvas even when the wrapped source stream is shared.
    """

    def __init__(
        self,
        source: FrameStream,
        options: DirtyRectangleOptions | None = None,
    ) -> None:
        self._source = source
        self._options = options or DirtyRectangleOptions()

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[AsyncIterator[bytes]]:
        async with self._source.subscribe() as frames:
            yield self._packets(frames)

    async def close(self) -> None:
        """Close the wrapped frame stream."""
        await self._source.close()

    async def _packets(self, frames: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        previous: RgbFrame | None = None
        async for frame in frames:
            previous, packet, metrics = await asyncio.to_thread(
                _encode_update,
                frame,
                previous,
                self._options,
            )
            logger.debug(
                "Dirty JPEG frame decode=%.2fms diff=%.2fms encode=%.2fms "
                "dirty=%.1f%% payload=%dB",
                metrics.decode_ms,
                metrics.diff_ms,
                metrics.encode_ms,
                metrics.dirty_ratio * 100,
                len(packet) if packet is not None else 0,
            )
            if packet is not None:
                yield packet


@dataclass(frozen=True, slots=True)
class _Metrics:
    decode_ms: float
    diff_ms: float
    encode_ms: float
    dirty_ratio: float


def _encode_update(
    frame_data: bytes,
    previous: RgbFrame | None,
    options: DirtyRectangleOptions,
) -> tuple[RgbFrame, bytes | None, _Metrics]:
    started = time.perf_counter()
    with Image.open(io.BytesIO(frame_data)) as image:
        current = np.array(image.convert("RGB"), dtype=np.uint8)
    decoded = time.perf_counter()

    height, width, _ = current.shape
    if width > 0xFFFF or height > 0xFFFF:
        raise ValueError("Dirty rectangle JPEG stream supports canvases up to 65535px")

    rows = (height + options.tile_height - 1) // options.tile_height
    columns = (width + options.tile_width - 1) // options.tile_width
    if previous is None or previous.shape != current.shape:
        dirty_tiles = np.ones((rows, columns), dtype=np.bool_)
    else:
        changed_pixels = np.any(current != previous, axis=2)
        padded = np.pad(
            changed_pixels,
            (
                (0, rows * options.tile_height - height),
                (0, columns * options.tile_width - width),
            ),
        )
        dirty_tiles = padded.reshape(
            rows,
            options.tile_height,
            columns,
            options.tile_width,
        ).any(axis=(1, 3))
    diffed = time.perf_counter()

    dirty_positions = np.argwhere(dirty_tiles)
    if not len(dirty_positions):
        return current, None, _Metrics(
            decode_ms=(decoded - started) * 1000,
            diff_ms=(diffed - decoded) * 1000,
            encode_ms=0,
            dirty_ratio=0,
        )

    parts = [
        _FRAME_HEADER.pack(_MAGIC, _VERSION, width, height, len(dirty_positions))
    ]
    for row, column in dirty_positions:
        x = int(column) * options.tile_width
        y = int(row) * options.tile_height
        patch_width = min(options.tile_width, width - x)
        patch_height = min(options.tile_height, height - y)
        patch = Image.fromarray(
            current[y : y + patch_height, x : x + patch_width]
        )
        output = io.BytesIO()
        patch.save(output, format="JPEG", quality=options.jpeg_quality)
        jpeg = output.getvalue()
        parts.extend(
            (
                _PATCH_HEADER.pack(
                    x,
                    y,
                    patch_width,
                    patch_height,
                    len(jpeg),
                ),
                jpeg,
            )
        )
    encoded = time.perf_counter()
    return current, b"".join(parts), _Metrics(
        decode_ms=(decoded - started) * 1000,
        diff_ms=(diffed - decoded) * 1000,
        encode_ms=(encoded - diffed) * 1000,
        dirty_ratio=len(dirty_positions) / dirty_tiles.size,
    )
