from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket, status

from control_plane.features.browsers.application.exceptions import (
    BrowserNotFoundException,
)
from control_plane.features.browsers.application.service import BrowserService
from control_plane.features.browsers.infrastructure.websocket_proxy import (
    proxy_websocket,
)
from control_plane.features.browsers.presentation.errors import (
    BROWSER_CAPACITY_EXHAUSTED,
    BROWSER_NOT_FOUND,
)
from control_plane.features.browsers.presentation.mapper import (
    to_browser_list_response,
    to_browser_response,
)
from control_plane.features.browsers.presentation.schemas import BrowserResponse
from control_plane.presentation.api_errors import api_error_responses

browser_router = APIRouter(route_class=DishkaRoute, tags=["browsers"])


@browser_router.post(
    "/browsers",
    response_model=BrowserResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_browser",
    responses=api_error_responses(BROWSER_CAPACITY_EXHAUSTED),
)
async def create_browser(service: FromDishka[BrowserService]) -> BrowserResponse:
    return to_browser_response(await service.create())


@browser_router.get(
    "/browsers",
    response_model=list[BrowserResponse],
    operation_id="list_browsers",
)
async def list_browsers(service: FromDishka[BrowserService]) -> list[BrowserResponse]:
    return to_browser_list_response(service.list())


@browser_router.get(
    "/browsers/{browser_id}",
    response_model=BrowserResponse,
    operation_id="get_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def get_browser(
    browser_id: UUID, service: FromDishka[BrowserService]
) -> BrowserResponse:
    return to_browser_response(service.get(browser_id))


@browser_router.delete(
    "/browsers/{browser_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="destroy_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def destroy_browser(
    browser_id: UUID, service: FromDishka[BrowserService]
) -> None:
    await service.destroy(browser_id)


@browser_router.post(
    "/browsers/{browser_id}/reset",
    response_model=BrowserResponse,
    operation_id="reset_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def reset_browser(
    browser_id: UUID, service: FromDishka[BrowserService]
) -> BrowserResponse:
    return to_browser_response(await service.reset(browser_id))


@browser_router.websocket("/browsers/{browser_id}/cdp")
@inject
async def browser_cdp(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    await _serve_browser(browser_id, websocket, service)


@browser_router.websocket("/browsers/{browser_id}/ws")
@inject
async def browser_socket(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    """Compatibility alias for clients using the original tunnel route."""
    await _serve_browser(browser_id, websocket, service)


async def _serve_browser(
    browser_id: UUID, websocket: WebSocket, service: BrowserService
) -> None:
    try:
        slot = service.slot(browser_id)
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_websocket(websocket, slot.tunnel_url)
