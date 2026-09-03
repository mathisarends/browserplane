from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, HTTPException, Response, WebSocket, status

from control_plane.proxy import proxy_websocket
from control_plane.registry import BrowserDescriptor, BrowserNotFoundError
from control_plane.services import BrowserService, BrowserUnavailableError

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/browsers", response_model=BrowserDescriptor, status_code=status.HTTP_201_CREATED
)
async def create_browser(
    service: FromDishka[BrowserService],
) -> BrowserDescriptor:
    try:
        return await service.create()
    except BrowserUnavailableError as error:
        raise HTTPException(
            status_code=409, detail="Browser capacity exhausted"
        ) from error


@router.get("/browsers", response_model=list[BrowserDescriptor])
async def list_browsers(service: FromDishka[BrowserService]) -> list[BrowserDescriptor]:
    return service.list()


@router.get("/browsers/{browser_id}", response_model=BrowserDescriptor)
async def get_browser(
    browser_id: UUID, service: FromDishka[BrowserService]
) -> BrowserDescriptor:
    try:
        return service.get(browser_id)
    except BrowserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Browser not found") from error


@router.delete("/browsers/{browser_id}", status_code=status.HTTP_204_NO_CONTENT)
async def destroy_browser(
    browser_id: UUID, service: FromDishka[BrowserService]
) -> Response:
    try:
        await service.destroy(browser_id)
    except BrowserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Browser not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/browsers/{browser_id}/reset", response_model=BrowserDescriptor)
async def reset_browser(
    browser_id: UUID, service: FromDishka[BrowserService]
) -> BrowserDescriptor:
    try:
        return await service.reset(browser_id)
    except BrowserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Browser not found") from error


async def _serve_browser(
    browser_id: UUID, websocket: WebSocket, service: BrowserService
) -> None:
    try:
        slot = service.slot(browser_id)
    except BrowserNotFoundError:
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_websocket(websocket, slot.tunnel_url)


@router.websocket("/browsers/{browser_id}/cdp")
@inject
async def browser_cdp(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    await _serve_browser(browser_id, websocket, service)


@router.websocket("/browsers/{browser_id}/ws")
@inject
async def browser_socket(
    browser_id: UUID,
    websocket: WebSocket,
    service: FromDishka[BrowserService],
) -> None:
    """Compatibility alias for clients using the original tunnel route."""
    await _serve_browser(browser_id, websocket, service)
