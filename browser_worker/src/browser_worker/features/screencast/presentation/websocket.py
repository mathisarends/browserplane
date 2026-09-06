import logging
import time
from contextlib import suppress
from uuid import UUID

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

from browser_worker.features.browser.application.exceptions import (
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.features.screencast.application.service import ScreencastService

logger = logging.getLogger(__name__)

_UNKNOWN_BROWSER_CLOSE_CODE = 1008
_INTERNAL_ERROR_CLOSE_CODE = 1011


async def resolve_frames(
    websocket: WebSocket,
    browser_id: UUID,
    browsers: BrowserService,
    screencasts: ScreencastService,
) -> FrameStream | None:
    """Return the browser's frame stream, closing the socket when it is gone."""
    try:
        return screencasts.for_browser(browsers.upstream_cdp_url(browser_id))
    except BrowserNotFoundException:
        await websocket.close(
            code=_UNKNOWN_BROWSER_CLOSE_CODE, reason="Unknown browser"
        )
        return None


async def stream_to_websocket(
    websocket: WebSocket, stream: FrameStream, *, name: str
) -> None:
    """Accept the socket and forward every packet the stream produces."""
    await websocket.accept()
    try:
        async with stream.subscribe() as packets:
            async for packet in packets:
                started = time.perf_counter()
                await websocket.send_bytes(packet)
                logger.debug(
                    "%s send=%.2fms payload=%dB",
                    name,
                    (time.perf_counter() - started) * 1000,
                    len(packet),
                )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("%s websocket stopped unexpectedly", name)
        await _close_if_connected(websocket, reason=f"{name} unavailable")


async def _close_if_connected(websocket: WebSocket, *, reason: str) -> None:
    if websocket.application_state is not WebSocketState.DISCONNECTED:
        with suppress(Exception):
            await websocket.close(code=_INTERNAL_ERROR_CLOSE_CODE, reason=reason)
