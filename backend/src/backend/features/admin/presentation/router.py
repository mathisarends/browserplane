from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from backend.features.admin.application.service import AdminService
from backend.features.admin.presentation.mapper import (
    to_browser_response,
    to_pooled_browser_response,
)
from backend.features.admin.presentation.schemas import PooledBrowserResponse
from backend.features.browsers.presentation.errors import (
    BROWSER_NOT_FOUND,
    BROWSER_PROVISIONING_FAILED,
)
from backend.features.sessions.presentation.mapper import to_session_response
from backend.features.sessions.presentation.schemas import SessionResponse
from backend.presentation.api_errors import api_error_responses

admin_router = APIRouter(prefix="/admin", route_class=DishkaRoute, tags=["admin"])


@admin_router.get(
    "/browsers",
    response_model=list[PooledBrowserResponse],
    operation_id="list_pooled_browsers",
)
async def list_pooled_browsers(
    service: FromDishka[AdminService],
) -> list[PooledBrowserResponse]:
    """The whole pool, including the browsers no session can be opened on."""
    pooled = await service.list_browsers()
    return [to_pooled_browser_response(browser) for browser in pooled]


@admin_router.delete(
    "/browsers/{browser_id}",
    response_model=PooledBrowserResponse,
    operation_id="destroy_pooled_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND, BROWSER_PROVISIONING_FAILED),
)
async def destroy_pooled_browser(
    browser_id: UUID, service: FromDishka[AdminService]
) -> PooledBrowserResponse:
    """Stop the browser process. Its session, if any, is dropped with it."""
    return to_browser_response(await service.destroy_browser(browser_id))


@admin_router.post(
    "/browsers/{browser_id}/restart",
    response_model=PooledBrowserResponse,
    operation_id="restart_pooled_browser",
    responses=api_error_responses(BROWSER_NOT_FOUND, BROWSER_PROVISIONING_FAILED),
)
async def restart_pooled_browser(
    browser_id: UUID, service: FromDishka[AdminService]
) -> PooledBrowserResponse:
    """Put a fresh browser behind the slot and hand it back to the pool."""
    return to_browser_response(await service.restart_browser(browser_id))


@admin_router.get(
    "/sessions",
    response_model=list[SessionResponse],
    operation_id="list_sessions",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def list_sessions(service: FromDishka[AdminService]) -> list[SessionResponse]:
    """Active and suspended sessions in one list, newest first."""
    sessions = await service.list_sessions()
    return [to_session_response(session) for session in sessions]
