from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import Query, WebSocket
from fastapi_canon import CanonRouter

from browser_worker.features.browser.application import BrowserService
from browser_worker.features.screencast.application import (
    FramePackager,
    ScreencastMode,
    ScreencastService,
)
from browser_worker.features.screencast.presentation.websocket import (
    resolve_frames,
    stream_to_websocket,
)

screencast_router = CanonRouter(tags=["browsers"], route_class=DishkaRoute)


@screencast_router.websocket("/browser/screencast")
@inject
async def browser_screencast(
    websocket: WebSocket,
    browsers: FromDishka[BrowserService],
    screencasts: FromDishka[ScreencastService],
    packager: FromDishka[FramePackager],
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
        packager(frames, mode),
        name=f"Browser screencast ({mode})",
    )
