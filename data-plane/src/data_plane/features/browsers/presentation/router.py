import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Response, WebSocket, status
from starlette.websockets import WebSocketDisconnect, WebSocketState

from data_plane.features.browsers.application.exceptions import BrowserNotFoundException
from data_plane.features.browsers.application.service import BrowserService
from data_plane.features.browsers.infrastructure.screencast import (
    ActiveTabFrame,
    ActiveTabStreams,
    PageUpdate,
)
from data_plane.features.browsers.infrastructure.screencast.fmp4 import Fmp4Livestream
from data_plane.features.browsers.infrastructure.screencast.tasks import cancel_and_wait
from data_plane.features.browsers.infrastructure.websocket_proxy import proxy_cdp
from data_plane.features.browsers.presentation.errors import (
    BROWSER_ALREADY_RUNNING,
    BROWSER_NOT_FOUND,
    BROWSER_STARTUP_FAILED,
)
from data_plane.features.browsers.presentation.mapper import to_browser_response
from data_plane.features.browsers.presentation.schemas import (
    BrowserResponse,
    CreateBrowserRequest,
)
from data_plane.presentation.api_errors import api_error_responses

browser_router = APIRouter(tags=["browsers"], route_class=DishkaRoute)
logger = logging.getLogger(__name__)


@browser_router.post(
    "/browser",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_browser",
    responses=api_error_responses(BROWSER_ALREADY_RUNNING, BROWSER_STARTUP_FAILED),
)
async def create_browser(
    request: CreateBrowserRequest,
    service: FromDishka[BrowserService],
) -> BrowserResponse:
    browser = await service.create(request.id)
    return to_browser_response(browser)


@browser_router.get(
    "/browser",
    operation_id="inspect_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def inspect_browser(service: FromDishka[BrowserService]) -> BrowserResponse:
    browser = service.get()
    return to_browser_response(browser)


@browser_router.delete(
    "/browser",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="destroy_browser",
)
async def destroy_browser(service: FromDishka[BrowserService]) -> Response:
    await service.destroy()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@browser_router.websocket("/browser/{browser_id}/cdp")
@inject
async def browser_cdp(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    try:
        upstream_url = service.upstream_cdp_url(browser_id)
    except BrowserNotFoundException:
        await websocket.accept()
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_cdp(websocket, upstream_url)


@browser_router.websocket("/browser/{browser_id}/screencast")
@inject
async def browser_screencast(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
    streams: FromDishka[ActiveTabStreams],
) -> None:
    try:
        upstream_url = service.upstream_cdp_url(browser_id)
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await websocket.accept()
    try:
        async with streams.for_browser(upstream_url).subscribe() as subscription:
            async for update in subscription.updates:
                if isinstance(update, ActiveTabFrame):
                    await websocket.send_bytes(update.data)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Screencast websocket stopped unexpectedly")
        if websocket.application_state is not WebSocketState.DISCONNECTED:
            with suppress(Exception):
                await websocket.close(
                    code=1011, reason="Browser screencast unavailable"
                )


@browser_router.websocket("/browser/{browser_id}/screencast/fmp4")
@inject
async def browser_fmp4_screencast(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
    streams: FromDishka[ActiveTabStreams],
) -> None:
    """Stream the active tab as fragmented MP4 without changing the raw route."""
    try:
        upstream_url = service.upstream_cdp_url(browser_id)
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return

    await websocket.accept()
    livestream = Fmp4Livestream()
    publisher: asyncio.Task[None] | None = None
    try:
        await livestream.start()
        async with (
            streams.for_browser(upstream_url).subscribe() as subscription,
            livestream.stream() as chunks,
        ):
            publisher = asyncio.create_task(
                _publish_fmp4_frames(subscription.updates, livestream),
                name="screencast:fmp4-publisher",
            )
            async for chunk in chunks:
                await websocket.send_bytes(chunk)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("fMP4 screencast websocket stopped unexpectedly")
        if websocket.application_state is not WebSocketState.DISCONNECTED:
            with suppress(Exception):
                await websocket.close(
                    code=1011, reason="Encoded browser screencast unavailable"
                )
    finally:
        if publisher is not None:
            await cancel_and_wait(publisher)
        await livestream.stop()


async def _publish_fmp4_frames(
    updates: AsyncGenerator[PageUpdate], livestream: Fmp4Livestream
) -> None:
    try:
        async for update in updates:
            if isinstance(update, ActiveTabFrame):
                await livestream.publish_frame(update.data)
    finally:
        await livestream.stop()
