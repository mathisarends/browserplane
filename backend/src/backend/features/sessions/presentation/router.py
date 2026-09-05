from collections.abc import Awaitable
from datetime import timedelta
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, WebSocket, status

from backend.features.browsers.application.exceptions import BrowserNotFoundException
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.infrastructure.websocket_proxy import proxy_stream
from backend.features.sessions.presentation.errors import (
    NO_BROWSER_AVAILABLE,
    SESSION_NOT_FOUND,
)
from backend.features.sessions.presentation.mapper import to_session_response
from backend.features.sessions.presentation.schemas import (
    OpenSessionRequest,
    SessionResponse,
)
from backend.presentation.api_errors import api_error_responses

session_router = APIRouter(route_class=DishkaRoute, tags=["sessions"])


@session_router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="open_session",
    responses=api_error_responses(NO_BROWSER_AVAILABLE),
)
async def open_session(
    request: OpenSessionRequest, service: FromDishka[SessionService]
) -> SessionResponse:
    session = await service.open(
        owner_id=request.owner_id, ttl=timedelta(seconds=request.ttl_seconds)
    )
    return to_session_response(session)


@session_router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    operation_id="get_session",
    responses=api_error_responses(SESSION_NOT_FOUND),
)
async def get_session(
    session_id: UUID, service: FromDishka[SessionService]
) -> SessionResponse:
    session = await service.get(session_id)
    return to_session_response(session)


@session_router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="close_session",
    responses=api_error_responses(SESSION_NOT_FOUND),
)
async def close_session(session_id: UUID, service: FromDishka[SessionService]) -> None:
    await service.close(session_id)


@session_router.websocket("/sessions/{session_id}/tunnel")
@inject
async def session_tunnel(
    session_id: UUID, websocket: WebSocket, service: FromDishka[SessionService]
) -> None:
    pending = service.upstream_tunnel_url(session_id)
    upstream_url = await _resolve(websocket, pending)
    if upstream_url is not None:
        await proxy_stream(websocket, upstream_url, name="Browser tunnel")


@session_router.websocket("/sessions/{session_id}/screencast")
@inject
async def session_screencast(
    session_id: UUID, websocket: WebSocket, service: FromDishka[SessionService]
) -> None:
    pending = service.upstream_screencast_url(session_id)
    upstream_url = await _resolve(websocket, pending)
    if upstream_url is not None:
        await proxy_stream(websocket, upstream_url, name="Screencast")


async def _resolve(websocket: WebSocket, pending: Awaitable[str]) -> str | None:
    """Await an upstream URL, closing the socket in session terms when it is gone."""
    try:
        return await pending
    except LeaseNotFoundException, BrowserNotFoundException:
        await websocket.accept()
        await websocket.close(code=1008, reason="Session not found")
        return None
