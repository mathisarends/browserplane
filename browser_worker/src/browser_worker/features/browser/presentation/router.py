from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import WebSocket, status
from fastapi_canon import CanonRouter, ErrorRegistry

from browser_worker.features.browser.application import (
    BrowserEndpoint,
    BrowserNotFoundException,
    BrowserService,
)
from browser_worker.features.browser.presentation.errors import (
    BROWSER_ALREADY_RUNNING,
    BROWSER_NOT_FOUND,
    BROWSER_STARTUP_FAILED,
)
from browser_worker.features.browser.presentation.schemas import (
    BrowserResponse,
    CreateBrowserRequest,
)
from browser_worker.features.browser.presentation.websocket_proxy import proxy_cdp
from browser_worker.features.downloads.application import DownloadService

_ROUTE_ERRORS = ErrorRegistry(
    name="browser-routes",
    errors=(
        BROWSER_ALREADY_RUNNING,
        BROWSER_STARTUP_FAILED,
        BROWSER_NOT_FOUND,
    ),
)

browser_router = CanonRouter(
    tags=["browsers"], route_class=DishkaRoute, error_registry=_ROUTE_ERRORS
)


@browser_router.post(
    "/browser",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_browser",
    raises=(BROWSER_ALREADY_RUNNING, BROWSER_STARTUP_FAILED, BROWSER_NOT_FOUND),
)
async def create_browser(
    request: CreateBrowserRequest,
    service: FromDishka[BrowserService],
    downloads: FromDishka[DownloadService],
    settings: FromDishka[BrowserEndpoint],
) -> BrowserResponse:
    await service.create(request.generation)
    await downloads.start()
    return BrowserResponse.from_browser(
        browser=service.inspect(), public_base_url=settings.public_base_url
    )


@browser_router.get(
    "/browser",
    operation_id="inspect_browser",
    raises=(BROWSER_NOT_FOUND,),
)
async def inspect_browser(
    service: FromDishka[BrowserService],
    settings: FromDishka[BrowserEndpoint],
) -> BrowserResponse:
    return BrowserResponse.from_browser(
        browser=service.inspect(), public_base_url=settings.public_base_url
    )


@browser_router.websocket("/browser/cdp")
@inject
async def browser_cdp(
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    try:
        upstream_url = service.upstream_cdp_url()
    except BrowserNotFoundException:
        await websocket.accept()
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_cdp(websocket, upstream_url)
