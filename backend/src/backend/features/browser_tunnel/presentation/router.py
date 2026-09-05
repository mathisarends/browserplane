from fastapi import APIRouter

from backend.features.browser_tunnel.presentation.schemas import (
    browser_json_schema,
    browser_openrpc_schema,
)

browser_rpc_router = APIRouter(prefix="/browser", tags=["browser-rpc"])


@browser_rpc_router.get(
    "/schema.json", include_in_schema=False, operation_id="json_rpc_schema"
)
async def json_rpc_schema() -> dict:
    return browser_json_schema()


@browser_rpc_router.get(
    "/openrpc.json", include_in_schema=False, operation_id="open_rpc_schema"
)
async def open_rpc_schema() -> dict:
    return browser_openrpc_schema()
