from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, WebSocket

from browsertunnel.presentation.schemas import (
    browser_json_schema,
    browser_openrpc_schema,
)
from browsertunnel.presentation.session import BrowserSessionFactory

router = APIRouter(prefix="/api/v1/browser", tags=["browser-tunnel"])


@router.get("/schema.json", include_in_schema=False, operation_id="json_rpc_schema")
async def json_rpc_schema() -> dict:
    return browser_json_schema()


@router.get("/openrpc.json", include_in_schema=False, operation_id="open_rpc_schema")
async def open_rpc_schema() -> dict:
    return browser_openrpc_schema()


@router.websocket("/ws")
@inject
async def browser_socket(
    websocket: WebSocket,
    sessions: FromDishka[BrowserSessionFactory],
) -> None:
    session = sessions.create(websocket)
    await session.run()
