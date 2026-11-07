from collections.abc import Callable
from enum import StrEnum

from browser_worker.features.screencast.domain import FrameStream


class ScreencastMode(StrEnum):
    """How the captured frames are packaged for the client."""

    JPEG = "jpeg"
    DIRTY_RECTANGLES = "dirty-rectangles"
    FMP4 = "fmp4"


type FramePackager = Callable[[FrameStream, ScreencastMode], FrameStream]
