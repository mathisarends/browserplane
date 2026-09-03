from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket

from control_plane.proxy import proxy_websocket
from control_plane.registry import (
    BrowserDescriptor,
    BrowserNotFoundError,
    BrowserRegistry,
)

router = APIRouter(prefix="/api/v1", route_class=DishkaRoute)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/browsers")
async def list_browsers(
    registry: FromDishka[BrowserRegistry],
) -> list[BrowserDescriptor]:
    return registry.list()


async def _serve_browser(
    browser_id: str, websocket: WebSocket, registry: BrowserRegistry
) -> None:
    try:
        slot = registry.get(browser_id)
    except BrowserNotFoundError:
        await websocket.close(code=1008, reason="Unknown browser")
        return
    await proxy_websocket(websocket, slot.tunnel_url)


@router.websocket("/browsers/{browser_id}/ws")
@inject
async def browser_socket(
    browser_id: str,
    websocket: WebSocket,
    registry: FromDishka[BrowserRegistry],
) -> None:
    await _serve_browser(browser_id, websocket, registry)
