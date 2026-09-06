import io
import struct
import time

import numpy as np
import numpy.typing as npt
from PIL import Image

from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
)

from .models import EncodingMetrics, RgbFrame

# Each update is one websocket message:
#   frame header: magic, version, canvas width, canvas height, patch count
#   patch*: x, y, width, height, JPEG byte length, JPEG bytes
FRAME_HEADER = struct.Struct("!4sBHHI")
PATCH_HEADER = struct.Struct("!HHHHI")
MAGIC = b"DRJP"
VERSION = 1


def encode_update(
    frame_data: bytes,
    previous: RgbFrame | None,
    settings: DirtyRectangleSettings,
) -> tuple[RgbFrame, bytes | None, EncodingMetrics]:
    """Turn a complete frame into a packet holding only its changed tiles.

    Returns the frame to diff the next one against, the packet (``None`` when
    nothing changed) and what the pass cost. Without a previous frame every
    tile counts as dirty, which is what makes a fresh subscription start with
    a complete canvas.
    """
    started = time.perf_counter()
    with Image.open(io.BytesIO(frame_data)) as image:
        current = np.array(image.convert("RGB"), dtype=np.uint8)
    decoded = time.perf_counter()

    height, width, _ = current.shape
    if width > 0xFFFF or height > 0xFFFF:
        raise ValueError("Dirty rectangle JPEG stream supports canvases up to 65535px")

    rows = (height + settings.tile_height - 1) // settings.tile_height
    columns = (width + settings.tile_width - 1) // settings.tile_width
    dirty_tiles = _dirty_tiles(current, previous, rows, columns, settings)
    diffed = time.perf_counter()

    dirty_positions = np.argwhere(dirty_tiles)
    if not len(dirty_positions):
        return (
            current,
            None,
            EncodingMetrics(
                decode_ms=(decoded - started) * 1000,
                diff_ms=(diffed - decoded) * 1000,
                encode_ms=0,
                dirty_ratio=0,
            ),
        )

    parts = [FRAME_HEADER.pack(MAGIC, VERSION, width, height, len(dirty_positions))]
    for row, column in dirty_positions:
        parts.extend(_encode_patch(current, int(row), int(column), settings))
    encoded = time.perf_counter()
    return (
        current,
        b"".join(parts),
        EncodingMetrics(
            decode_ms=(decoded - started) * 1000,
            diff_ms=(diffed - decoded) * 1000,
            encode_ms=(encoded - diffed) * 1000,
            dirty_ratio=len(dirty_positions) / dirty_tiles.size,
        ),
    )


def _dirty_tiles(
    current: RgbFrame,
    previous: RgbFrame | None,
    rows: int,
    columns: int,
    settings: DirtyRectangleSettings,
) -> npt.NDArray[np.bool_]:
    """Mark the tiles whose pixels differ from the previous frame."""
    if previous is None or previous.shape != current.shape:
        return np.ones((rows, columns), dtype=np.bool_)

    height, width, _ = current.shape
    changed_pixels = np.any(current != previous, axis=2)
    padded = np.pad(
        changed_pixels,
        (
            (0, rows * settings.tile_height - height),
            (0, columns * settings.tile_width - width),
        ),
    )
    return padded.reshape(
        rows,
        settings.tile_height,
        columns,
        settings.tile_width,
    ).any(axis=(1, 3))


def _encode_patch(
    current: RgbFrame,
    row: int,
    column: int,
    settings: DirtyRectangleSettings,
) -> tuple[bytes, bytes]:
    """Encode one dirty tile, clipped to the canvas at the last row or column."""
    height, width, _ = current.shape
    x = column * settings.tile_width
    y = row * settings.tile_height
    patch_width = min(settings.tile_width, width - x)
    patch_height = min(settings.tile_height, height - y)
    patch = Image.fromarray(current[y : y + patch_height, x : x + patch_width])
    output = io.BytesIO()
    patch.save(output, format="JPEG", quality=settings.jpeg_quality)
    jpeg = output.getvalue()
    return PATCH_HEADER.pack(x, y, patch_width, patch_height, len(jpeg)), jpeg
