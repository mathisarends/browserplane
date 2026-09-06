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
#   frame header: magic, version, canvas width, canvas height,
#                 tile width, tile height, patch count
#   patch*: x, y, width, height, JPEG byte length, JPEG bytes
FRAME_HEADER = struct.Struct("!4sBHHHHI")
PATCH_HEADER = struct.Struct("!HHHHI")
MAGIC = b"DRJP"
VERSION = 2

type TileGrid = npt.NDArray[np.bool_]
type TileRectangle = tuple[int, int, int, int]


def encode_update(
    frame_data: bytes,
    previous: RgbFrame | None,
    settings: DirtyRectangleSettings,
) -> tuple[RgbFrame, bytes | None, EncodingMetrics]:
    """Turn a complete frame into a packet holding only its changed pixels.

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

    dirty_tiles = _dirty_tiles(current, previous, settings)
    rectangles = _merge_rectangles(dirty_tiles)
    diffed = time.perf_counter()

    if not rectangles:
        return (
            current,
            None,
            EncodingMetrics(
                decode_ms=(decoded - started) * 1000,
                diff_ms=(diffed - decoded) * 1000,
                encode_ms=0,
                dirty_ratio=0,
                patches=0,
            ),
        )

    parts = [
        FRAME_HEADER.pack(
            MAGIC,
            VERSION,
            width,
            height,
            settings.tile_width,
            settings.tile_height,
            len(rectangles),
        )
    ]
    for rectangle in rectangles:
        parts.extend(_encode_region(current, rectangle, settings))
    encoded = time.perf_counter()
    return (
        current,
        b"".join(parts),
        EncodingMetrics(
            decode_ms=(decoded - started) * 1000,
            diff_ms=(diffed - decoded) * 1000,
            encode_ms=(encoded - diffed) * 1000,
            dirty_ratio=float(dirty_tiles.mean()),
            patches=len(rectangles),
        ),
    )


def _dirty_tiles(
    current: RgbFrame,
    previous: RgbFrame | None,
    settings: DirtyRectangleSettings,
) -> TileGrid:
    """Mark the tiles whose pixels differ from the previous frame.

    The comparison runs over the frame as rows of raw bytes, so the three
    channels of a pixel fall into the same tile column on their own. Reducing
    that with ``reduceat`` needs no padding to a whole number of tiles, which
    keeps the clipped last row and column free of an extra copy of the frame.
    """
    height, width, _ = current.shape
    rows = -(-height // settings.tile_height)
    columns = -(-width // settings.tile_width)
    if previous is None or previous.shape != current.shape:
        return np.ones((rows, columns), dtype=np.bool_)

    changed = current.reshape(height, width * 3) != previous.reshape(height, width * 3)
    row_starts = np.arange(rows) * settings.tile_height
    column_starts = np.arange(columns) * settings.tile_width * 3
    by_row = np.logical_or.reduceat(changed, row_starts, axis=0)
    return np.logical_or.reduceat(by_row, column_starts, axis=1)


def _merge_rectangles(dirty: TileGrid) -> list[TileRectangle]:
    """Cover the dirty tiles with as few rectangles as possible.

    Every JPEG pays for its own headers and quantization tables, so a tile grid
    fine enough to keep a caret or a hover state cheap would otherwise spend
    more on framing than on pixels. Neighbouring dirty tiles are merged into
    one rectangle - horizontally per row, then vertically across rows that
    share a span - and since a rectangle only ever spans tiles that are all
    dirty, this costs no extra pixels.
    """
    rectangles: list[TileRectangle] = []
    open_spans: dict[tuple[int, int], int] = {}
    for row in range(len(dirty)):
        spans = _row_spans(dirty[row])
        continued = {}
        for span in spans:
            continued[span] = open_spans.pop(span, row)
        for (start, end), top in open_spans.items():
            rectangles.append((top, start, row - top, end - start))
        open_spans = continued
    for (start, end), top in open_spans.items():
        rectangles.append((top, start, len(dirty) - top, end - start))
    return rectangles


def _row_spans(row: TileGrid) -> list[tuple[int, int]]:
    """The half-open column ranges of the dirty runs in one tile row."""
    edges = np.flatnonzero(np.diff(np.concatenate(([False], row, [False]))))
    return [(int(start), int(end)) for start, end in edges.reshape(-1, 2)]


def _encode_region(
    current: RgbFrame,
    rectangle: TileRectangle,
    settings: DirtyRectangleSettings,
) -> tuple[bytes, bytes]:
    """Encode one merged rectangle, clipped to the canvas at the right edges."""
    height, width, _ = current.shape
    top, left, tile_rows, tile_columns = rectangle
    x = left * settings.tile_width
    y = top * settings.tile_height
    region_width = min(tile_columns * settings.tile_width, width - x)
    region_height = min(tile_rows * settings.tile_height, height - y)
    region = Image.fromarray(current[y : y + region_height, x : x + region_width])
    output = io.BytesIO()
    region.save(
        output,
        format="JPEG",
        quality=settings.jpeg_quality,
        subsampling=settings.jpeg_subsampling,
        optimize=settings.optimize_jpeg,
    )
    jpeg = output.getvalue()
    return PATCH_HEADER.pack(x, y, region_width, region_height, len(jpeg)), jpeg
