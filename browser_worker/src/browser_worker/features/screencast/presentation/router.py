import asyncio
import logging
import time
from collections.abc import AsyncIterator
from contextlib import suppress
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from browser_worker.features.browser.application.exceptions import (
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.screencast.infrastructure.dirty_rectangles import (
    DirtyRectangleJpegStream,
    DirtyRectangleOptions,
)
from browser_worker.features.screencast.infrastructure.fmp4 import Fmp4Livestream
from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
)
from browser_worker.features.screencast.infrastructure.tasks import cancel_and_wait

screencast_router = APIRouter(tags=["browsers"], route_class=DishkaRoute)
logger = logging.getLogger(__name__)


@screencast_router.websocket("/browser/{browser_id}/screencast")
@inject
async def browser_screencast(
    browser_id: UUID,
    websocket: WebSocket,
    browsers: FromDishka[BrowserService],
    screencasts: FromDishka[ScreencastService],
) -> None:
    try:
        stream = screencasts.for_browser(browsers.upstream_cdp_url(browser_id))
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return

    await websocket.accept()
    try:
        async with stream.subscribe() as frames:
            async for frame in frames:
                await websocket.send_bytes(frame)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Screencast websocket stopped unexpectedly")
        await _close_if_connected(websocket, reason="Browser screencast unavailable")


@screencast_router.websocket("/browser/{browser_id}/screencast/dirty-rectangles")
@inject
async def browser_dirty_rectangle_screencast(
    browser_id: UUID,
    websocket: WebSocket,
    browsers: FromDishka[BrowserService],
    screencasts: FromDishka[ScreencastService],
    settings: FromDishka[DirtyRectangleSettings],
) -> None:
    try:
        source = screencasts.for_browser(browsers.upstream_cdp_url(browser_id))
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return

    stream = DirtyRectangleJpegStream(
        source,
        DirtyRectangleOptions(
            tile_width=settings.tile_width,
            tile_height=settings.tile_height,
            jpeg_quality=settings.jpeg_quality,
        ),
    )
    await websocket.accept()
    try:
        async with stream.subscribe() as packets:
            async for packet in packets:
                started = time.perf_counter()
                await websocket.send_bytes(packet)
                logger.debug(
                    "Dirty JPEG websocket send=%.2fms payload=%dB",
                    (time.perf_counter() - started) * 1000,
                    len(packet),
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Dirty rectangle screencast websocket stopped unexpectedly")
        await _close_if_connected(
            websocket, reason="Dirty rectangle screencast unavailable"
        )


@screencast_router.websocket("/browser/{browser_id}/screencast/fmp4")
@inject
async def browser_fmp4_screencast(
    browser_id: UUID,
    websocket: WebSocket,
    browsers: FromDishka[BrowserService],
    screencasts: FromDishka[ScreencastService],
) -> None:
    try:
        stream = screencasts.for_browser(browsers.upstream_cdp_url(browser_id))
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return

    await websocket.accept()
    livestream = Fmp4Livestream()
    publisher: asyncio.Task[None] | None = None
    try:
        await livestream.start()
        async with stream.subscribe() as frames, livestream.stream() as chunks:
            publisher = asyncio.create_task(
                _publish_fmp4_frames(frames, livestream),
                name="screencast:fmp4-publisher",
            )
            async for chunk in chunks:
                await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("fMP4 screencast websocket stopped unexpectedly")
        await _close_if_connected(
            websocket, reason="Encoded browser screencast unavailable"
        )
    finally:
        if publisher is not None:
            await cancel_and_wait(publisher)
        await livestream.stop()


async def _publish_fmp4_frames(
    frames: AsyncIterator[bytes], livestream: Fmp4Livestream
) -> None:
    try:
        async for frame in frames:
            await livestream.publish_frame(frame)
    finally:
        await livestream.stop()


async def _close_if_connected(websocket: WebSocket, *, reason: str) -> None:
    if websocket.application_state is not WebSocketState.DISCONNECTED:
        with suppress(Exception):
            await websocket.close(code=1011, reason=reason)
