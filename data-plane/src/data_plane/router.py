from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, HTTPException, Response, WebSocket
from pydantic import BaseModel

from data_plane.manager import (
    BrowserManager,
    BrowserNotFoundError,
    BrowserResource,
    CapacityExceededError,
)
from data_plane.proxy import proxy_cdp

router = APIRouter(prefix="/api/v1", route_class=DishkaRoute)


class CreateBrowserRequest(BaseModel):
    id: str


class Capacity(BaseModel):
    total: int
    available: int


@router.get("/health", operation_id="health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness", operation_id="readiness")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/capacity", operation_id="capacity")
async def capacity(manager: FromDishka[BrowserManager]) -> Capacity:
    total, available = manager.capacity()
    return Capacity(total=total, available=available)


@router.post("/browsers", status_code=201, operation_id="create_browser")
async def create_browser(
    request: CreateBrowserRequest,
    manager: FromDishka[BrowserManager],
) -> BrowserResource:
    try:
        return await manager.create(request.id)
    except CapacityExceededError as error:
        raise HTTPException(
            status_code=409, detail="Worker capacity exhausted"
        ) from error


@router.get("/browsers/{browser_id}", operation_id="inspect_browser")
async def inspect_browser(
    browser_id: str,
    manager: FromDishka[BrowserManager],
) -> BrowserResource:
    try:
        return manager.inspect(browser_id)
    except BrowserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Browser not found") from error


@router.delete(
    "/browsers/{browser_id}", status_code=204, operation_id="destroy_browser"
)
async def destroy_browser(
    browser_id: str,
    manager: FromDishka[BrowserManager],
) -> Response:
    await manager.destroy(browser_id)
    return Response(status_code=204)


@router.websocket("/browsers/{browser_id}/cdp")
@inject
async def browser_cdp(
    browser_id: str,
    websocket: WebSocket,
    manager: FromDishka[BrowserManager],
) -> None:
    try:
        upstream_url = manager.upstream_cdp_url(browser_id)
    except BrowserNotFoundError:
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_cdp(websocket, upstream_url)
