from enum import StrEnum
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Query, WebSocket

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.screencast.infrastructure.dirty_rectangles import (
    DirtyRectangleJpegStream,
)
from browser_worker.features.screencast.infrastructure.fmp4 import Fmp4FrameStream
from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
)
from browser_worker.features.screencast.presentation.websocket import (
    resolve_frames,
    stream_to_websocket,
)

screencast_router = APIRouter(tags=["browsers"], route_class=DishkaRoute)


class ScreencastMode(StrEnum):
    """How the captured frames are packaged for the client."""

    JPEG = "jpeg"
    DIRTY_RECTANGLES = "dirty-rectangles"
    FMP4 = "fmp4"


@screencast_router.websocket("/browser/screencast")
@inject
async def browser_screencast(
    websocket: WebSocket,
    browsers: FromDishka[BrowserService],
    screencasts: FromDishka[ScreencastService],
    settings: FromDishka[DirtyRectangleSettings],
    mode: Annotated[
        ScreencastMode, Query(description="How frames are packaged for the client")
    ] = ScreencastMode.JPEG,
) -> None:
    """Stream the browser's capture in the packaging the client asked for.

    All three modes read the same capture, so they differ only in what they put
    on the wire - which makes them one endpoint with a mode rather than three
    routes that would each have to be kept in step with the others.
    """
    frames = await resolve_frames(
        websocket,
        browsers=browsers,
        screencasts=screencasts,
    )
    if frames is None:
        return
    await stream_to_websocket(
        websocket,
        _packaged(frames, mode=mode, settings=settings),
        name=f"Browser screencast ({mode})",
    )


def _packaged(
    frames: FrameStream, *, mode: ScreencastMode, settings: DirtyRectangleSettings
) -> FrameStream:
    match mode:
        case ScreencastMode.JPEG:
            return frames
        case ScreencastMode.DIRTY_RECTANGLES:
            return DirtyRectangleJpegStream(frames, settings)
        case ScreencastMode.FMP4:
            return Fmp4FrameStream(frames)
