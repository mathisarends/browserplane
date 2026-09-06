from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket, status

from browser_worker.features.browser.application.exceptions import (
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.browser.infrastructure.settings import BrowserSettings
from browser_worker.features.browser.infrastructure.websocket_proxy import proxy_cdp
from browser_worker.features.browser.presentation.errors import (
    BROWSER_ALREADY_RUNNING,
    BROWSER_NOT_FOUND,
    BROWSER_STARTUP_FAILED,
)
from browser_worker.features.browser.presentation.mapper import to_browser_response
from browser_worker.features.browser.presentation.schemas import (
    BrowserResponse,
    CreateBrowserRequest,
)
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.presentation.api_errors import api_error_responses

browser_router = APIRouter(tags=["browsers"], route_class=DishkaRoute)


@browser_router.post(
    "/browser",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_browser",
    responses=api_error_responses(BROWSER_ALREADY_RUNNING, BROWSER_STARTUP_FAILED),
)
async def create_browser(
    request: CreateBrowserRequest,
    service: FromDishka[BrowserService],
    downloads: FromDishka[DownloadService],
    settings: FromDishka[BrowserSettings],
) -> BrowserResponse:
    browser_id = await service.create(request.id, request.generation)
    await downloads.start(browser_id)
    return to_browser_response(service.inspect(), settings.public_base_url)


@browser_router.get(
    "/browser",
    operation_id="inspect_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def inspect_browser(
    service: FromDishka[BrowserService],
    settings: FromDishka[BrowserSettings],
) -> BrowserResponse:
    return to_browser_response(service.inspect(), settings.public_base_url)


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
