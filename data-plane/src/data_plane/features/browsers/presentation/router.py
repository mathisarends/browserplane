from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Response, WebSocket, status

from data_plane.features.browsers.application.exceptions import BrowserNotFoundException
from data_plane.features.browsers.application.service import BrowserService
from data_plane.features.browsers.infrastructure.websocket_proxy import proxy_cdp
from data_plane.features.browsers.presentation.errors import (
    BROWSER_CAPACITY_EXHAUSTED,
    BROWSER_NOT_FOUND,
    BROWSER_STARTUP_FAILED,
)
from data_plane.features.browsers.presentation.mapper import (
    to_browser_response,
    to_capacity_response,
)
from data_plane.features.browsers.presentation.schemas import (
    BrowserResponse,
    CapacityResponse,
    CreateBrowserRequest,
)
from data_plane.presentation.api_errors import api_error_responses

browser_router = APIRouter(tags=["browsers"], route_class=DishkaRoute)


@browser_router.get("/capacity", operation_id="capacity")
async def capacity(service: FromDishka[BrowserService]) -> CapacityResponse:
    worker_capacity = service.capacity()
    return to_capacity_response(worker_capacity)


@browser_router.post(
    "/browsers",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_browser",
    responses=api_error_responses(BROWSER_CAPACITY_EXHAUSTED, BROWSER_STARTUP_FAILED),
)
async def create_browser(
    request: CreateBrowserRequest,
    service: FromDishka[BrowserService],
) -> BrowserResponse:
    browser = await service.create(request.id)
    return to_browser_response(browser)


@browser_router.get(
    "/browsers/{browser_id}",
    operation_id="inspect_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def inspect_browser(
    browser_id: str,
    service: FromDishka[BrowserService],
) -> BrowserResponse:
    browser = service.get(browser_id)
    return to_browser_response(browser)


@browser_router.delete(
    "/browsers/{browser_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="destroy_browser",
)
async def destroy_browser(
    browser_id: str,
    service: FromDishka[BrowserService],
) -> Response:
    await service.destroy(browser_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@browser_router.websocket("/browsers/{browser_id}/cdp")
@inject
async def browser_cdp(
    browser_id: str,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    try:
        upstream_url = service.upstream_cdp_url(browser_id)
    except BrowserNotFoundException:
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_cdp(websocket, upstream_url)
