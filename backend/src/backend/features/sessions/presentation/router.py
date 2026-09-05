import logging
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any
from uuid import UUID

from dishka import AsyncContainer, Scope
from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Response, WebSocket, status

from backend.browser_tunnel.presentation.session import BrowserTunnel
from backend.features.browsers.application.exceptions import BrowserNotFoundException
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.exceptions import (
    SessionNotActiveException,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.infrastructure.websocket_proxy import proxy_stream
from backend.features.sessions.presentation.errors import (
    BROWSER_STATE_TRANSFER_FAILED,
    NO_BROWSER_AVAILABLE,
    SESSION_NOT_ACTIVE,
    SESSION_NOT_FOUND,
    SESSION_NOT_SUSPENDED,
)
from backend.features.sessions.presentation.mapper import (
    to_browser_state_snapshot_response,
    to_session_response,
)
from backend.features.sessions.presentation.schemas import (
    BrowserStateSnapshotResponse,
    CaptureBrowserStateSnapshotRequest,
    OpenSessionRequest,
    ResumeSessionRequest,
    SessionResponse,
)
from backend.presentation.api_errors import api_error_responses
from generated.data_plane import AuthenticationStateSchema, BrowserStateSchema

session_router = APIRouter(route_class=DishkaRoute, tags=["sessions"])
logger = logging.getLogger(__name__)


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
        owner_id=request.owner_id,
        ttl=timedelta(seconds=request.ttl_seconds),
        authentication_state=(
            request.authentication_state.model_dump(mode="json", by_alias=True)
            if request.authentication_state is not None
            else None
        ),
        browser_state=(
            request.browser_state.model_dump(mode="json", by_alias=True)
            if request.browser_state is not None
            else None
        ),
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


@session_router.get(
    "/sessions/{session_id}/authentication-state",
    operation_id="capture_session_authentication_state",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def capture_session_authentication_state(
    session_id: UUID,
    response: Response,
    service: FromDishka[SessionService],
) -> AuthenticationStateSchema:
    state = await service.capture_authentication(session_id)
    response.headers["Cache-Control"] = "no-store"
    return AuthenticationStateSchema.model_validate(state)


@session_router.put(
    "/sessions/{session_id}/authentication-state",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="mount_session_authentication_state",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def mount_session_authentication_state(
    session_id: UUID,
    state: AuthenticationStateSchema,
    service: FromDishka[SessionService],
) -> Response:
    await service.mount_authentication(
        session_id, state.model_dump(mode="json", by_alias=True)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@session_router.get(
    "/sessions/{session_id}/browser-state",
    operation_id="capture_session_browser_state",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def capture_session_browser_state(
    session_id: UUID,
    response: Response,
    service: FromDishka[SessionService],
) -> BrowserStateSchema:
    state = await service.capture_browser(session_id)
    response.headers["Cache-Control"] = "no-store"
    return BrowserStateSchema.model_validate(state)


@session_router.put(
    "/sessions/{session_id}/browser-state",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="mount_session_browser_state",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def mount_session_browser_state(
    session_id: UUID,
    state: BrowserStateSchema,
    service: FromDishka[SessionService],
) -> Response:
    await service.mount_browser(
        session_id, state.model_dump(mode="json", by_alias=True)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@session_router.get(
    "/browser-state-snapshots",
    response_model=list[BrowserStateSnapshotResponse],
    operation_id="list_browser_state_snapshots",
)
async def list_browser_state_snapshots(
    response: Response,
    service: FromDishka[SessionService],
) -> list[BrowserStateSnapshotResponse]:
    response.headers["Cache-Control"] = "no-store"
    snapshots = await service.list_snapshots()
    return [to_browser_state_snapshot_response(snapshot) for snapshot in snapshots]


@session_router.post(
    "/sessions/{session_id}/browser-state-snapshots",
    response_model=BrowserStateSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="capture_browser_state_snapshot",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def capture_browser_state_snapshot(
    session_id: UUID,
    request: CaptureBrowserStateSnapshotRequest,
    service: FromDishka[SessionService],
) -> BrowserStateSnapshotResponse:
    snapshot = await service.capture_snapshot(
        session_id,
        name=request.name,
        source_browser=request.source_browser,
    )
    return to_browser_state_snapshot_response(snapshot)


@session_router.post(
    "/sessions/{session_id}/suspend",
    response_model=SessionResponse,
    operation_id="suspend_session",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def suspend_session(
    session_id: UUID, service: FromDishka[SessionService]
) -> SessionResponse:
    """Park a session: store what its browser holds and free the browser."""
    suspended = await service.suspend(session_id)
    return to_session_response(suspended)


@session_router.post(
    "/sessions/{session_id}/resume",
    response_model=SessionResponse,
    operation_id="resume_session",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_SUSPENDED,
        NO_BROWSER_AVAILABLE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def resume_session(
    session_id: UUID,
    request: ResumeSessionRequest,
    service: FromDishka[SessionService],
) -> SessionResponse:
    """Mount a parked session onto whichever browser is free now."""
    session = await service.resume(
        session_id, ttl=timedelta(seconds=request.ttl_seconds)
    )
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
    session_id: UUID,
    websocket: WebSocket,
    container: FromDishka[AsyncContainer],
    tunnel: FromDishka[BrowserTunnel],
) -> None:
    cdp_url = await _resolve(
        websocket, container, lambda service: service.upstream_cdp_url(session_id)
    )
    if cdp_url is None:
        return
    try:
        logger.info("Session tunnel connected session_id=%s", session_id)
        await tunnel.serve(websocket, cdp_url)
    finally:
        # State capture is an independent HTTP operation. Keep the lease alive
        # when this transport drops so state can still be read from the worker.
        # DELETE /sessions/{id} or the TTL releases the browser.
        logger.info(
            "Session tunnel disconnected; lease remains active session_id=%s",
            session_id,
        )


@session_router.websocket("/sessions/{session_id}/screencast")
@inject
async def session_screencast(
    session_id: UUID, websocket: WebSocket, container: FromDishka[AsyncContainer]
) -> None:
    upstream_url = await _resolve(
        websocket,
        container,
        lambda service: service.upstream_screencast_url(session_id),
    )
    if upstream_url is not None:
        await proxy_stream(websocket, upstream_url, name="Screencast")


@session_router.websocket("/sessions/{session_id}/screencast/fmp4")
@inject
async def session_fmp4_screencast(
    session_id: UUID, websocket: WebSocket, container: FromDishka[AsyncContainer]
) -> None:
    upstream_url = await _resolve(
        websocket,
        container,
        lambda service: service.upstream_fmp4_screencast_url(session_id),
    )
    if upstream_url is not None:
        await proxy_stream(websocket, upstream_url, name="fMP4 screencast")


@asynccontextmanager
async def _session_service(
    container: AsyncContainer,
) -> AsyncGenerator[SessionService]:
    """
    A service for one step of a live connection.

    A stream outlives any unit of work, so each lookup gets its own scope and
    hands its database session back before the proxying starts.
    """
    async with container(scope=Scope.REQUEST) as scoped:
        yield await scoped.get(SessionService)


async def _resolve(
    websocket: WebSocket,
    container: AsyncContainer,
    resolve: Callable[[SessionService], Coroutine[Any, Any, str]],
) -> str | None:
    """Look up an upstream URL, closing the socket in session terms when it is gone."""
    try:
        async with _session_service(container) as service:
            return await resolve(service)
    except LeaseNotFoundException, BrowserNotFoundException, SessionNotActiveException:
        await websocket.accept()
        await websocket.close(code=1008, reason="Session not found")
        return None
