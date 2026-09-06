import logging
from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka, inject
from fastapi import APIRouter, Query, Response, WebSocket, status

from backend.features.browser_tunnel.presentation.session import BrowserTunnel
from backend.features.browsers.application.exceptions import BrowserNotFoundException
from backend.features.browsers.infrastructure.routes import (
    BrowserWorkerRoutes,
    ScreencastMode,
)
from backend.features.browsers.presentation.errors import BROWSER_NOT_FOUND
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.exceptions import (
    SessionNotActiveException,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.domain.models import ResolvedSession
from backend.features.sessions.infrastructure.lease_keeper import SessionLeaseKeeper
from backend.features.sessions.infrastructure.websocket_proxy import proxy_stream
from backend.features.sessions.presentation.errors import (
    AUTHENTICATION_PROFILE_NOT_FOUND,
    BROWSER_CHECKPOINT_NOT_FOUND,
    BROWSER_STATE_TRANSFER_FAILED,
    DOWNLOAD_NOT_FOUND,
    SESSION_NOT_ACTIVE,
    SESSION_NOT_FOUND,
)
from backend.features.sessions.presentation.mapper import (
    to_authentication_profile_response,
    to_browser_checkpoint_response,
    to_owner_sessions_response,
    to_session_response,
)
from backend.features.sessions.presentation.schemas import (
    AuthenticationProfileResponse,
    BrowserCheckpointResponse,
    CreateAuthenticationProfileRequest,
    CreateBrowserCheckpointRequest,
    MountAuthenticationProfileRequest,
    MountBrowserCheckpointRequest,
    OwnerSessionsResponse,
    SessionResponse,
    UpdateAuthenticationProfileRequest,
)
from backend.presentation.api_errors import api_error_responses
from generated.browser_worker import BrowserStateSchema, DownloadResponse

session_router = APIRouter(route_class=DishkaRoute, tags=["sessions"])
logger = logging.getLogger(__name__)


@session_router.get(
    "/sessions",
    response_model=OwnerSessionsResponse,
    operation_id="list_owner_sessions",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def list_owner_sessions(
    owner_id: UUID, service: FromDishka[SessionService]
) -> OwnerSessionsResponse:
    """What one client still owns, so a reloaded page can pick it back up."""
    return to_owner_sessions_response(
        await service.list(owner_id=owner_id),
        remaining_capacity=await service.remaining_capacity(),
    )


@session_router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    operation_id="get_session",
    responses=api_error_responses(SESSION_NOT_FOUND, BROWSER_NOT_FOUND),
)
async def get_session(
    session_id: UUID, service: FromDishka[SessionService]
) -> SessionResponse:
    session = await service.get(session_id)
    return to_session_response(session)


@session_router.put(
    "/sessions/{session_id}/authentication-profile",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="mount_session_authentication_profile",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        AUTHENTICATION_PROFILE_NOT_FOUND,
        BROWSER_CHECKPOINT_NOT_FOUND,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def mount_session_authentication_profile(
    session_id: UUID,
    request: MountAuthenticationProfileRequest,
    service: FromDishka[SessionService],
) -> Response:
    await service.mount_authentication_profile(
        session_id, request.authentication_profile_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@session_router.get(
    "/sessions/{session_id}/browser-state",
    operation_id="capture_session_browser_state",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        AUTHENTICATION_PROFILE_NOT_FOUND,
        BROWSER_CHECKPOINT_NOT_FOUND,
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
        BROWSER_NOT_FOUND,
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
    "/sessions/{session_id}/downloads",
    operation_id="list_session_downloads",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def list_session_downloads(
    session_id: UUID,
    response: Response,
    service: FromDishka[SessionService],
) -> list[DownloadResponse]:
    response.headers["Cache-Control"] = "no-store"
    return await service.list_downloads(session_id)


@session_router.get(
    "/sessions/{session_id}/downloads/{download_id}/file",
    operation_id="download_session_file",
    responses={
        200: {
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
            "description": "Downloaded file",
        },
        **api_error_responses(
            SESSION_NOT_FOUND,
            BROWSER_NOT_FOUND,
            SESSION_NOT_ACTIVE,
            DOWNLOAD_NOT_FOUND,
            BROWSER_STATE_TRANSFER_FAILED,
        ),
    },
)
async def download_session_file(
    session_id: UUID,
    download_id: str,
    service: FromDishka[SessionService],
) -> Response:
    filename, content = await service.download_file(session_id, download_id)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )


@session_router.get(
    "/browser-checkpoints",
    response_model=list[BrowserCheckpointResponse],
    operation_id="list_browser_checkpoints",
)
async def list_browser_checkpoints(
    response: Response,
    service: FromDishka[SessionService],
) -> list[BrowserCheckpointResponse]:
    response.headers["Cache-Control"] = "no-store"
    checkpoints = await service.list_browser_checkpoints()
    return [to_browser_checkpoint_response(item) for item in checkpoints]


@session_router.post(
    "/sessions/{session_id}/browser-checkpoints",
    response_model=BrowserCheckpointResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_browser_checkpoint",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def create_browser_checkpoint(
    session_id: UUID,
    request: CreateBrowserCheckpointRequest,
    service: FromDishka[SessionService],
) -> BrowserCheckpointResponse:
    checkpoint = await service.create_browser_checkpoint(
        session_id,
        authentication_profile_id=request.authentication_profile_id,
    )
    return to_browser_checkpoint_response(checkpoint)


@session_router.get(
    "/authentication-profiles",
    response_model=list[AuthenticationProfileResponse],
    operation_id="list_authentication_profiles",
)
async def list_authentication_profiles(
    response: Response,
    service: FromDishka[SessionService],
) -> list[AuthenticationProfileResponse]:
    response.headers["Cache-Control"] = "no-store"
    profiles = await service.list_authentication_profiles()
    return [to_authentication_profile_response(item) for item in profiles]


@session_router.post(
    "/sessions/{session_id}/authentication-profiles",
    response_model=AuthenticationProfileResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_authentication_profile",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def create_authentication_profile(
    session_id: UUID,
    request: CreateAuthenticationProfileRequest,
    service: FromDishka[SessionService],
) -> AuthenticationProfileResponse:
    profile = await service.create_authentication_profile(
        session_id,
        name=request.name,
    )
    return to_authentication_profile_response(profile)


@session_router.get(
    "/authentication-profiles/{profile_id}",
    response_model=AuthenticationProfileResponse,
    operation_id="get_authentication_profile",
    responses=api_error_responses(AUTHENTICATION_PROFILE_NOT_FOUND),
)
async def get_authentication_profile(
    profile_id: UUID,
    response: Response,
    service: FromDishka[SessionService],
) -> AuthenticationProfileResponse:
    response.headers["Cache-Control"] = "no-store"
    return to_authentication_profile_response(
        await service.get_authentication_profile(profile_id)
    )


@session_router.put(
    "/sessions/{session_id}/authentication-profiles/{profile_id}",
    response_model=AuthenticationProfileResponse,
    operation_id="update_authentication_profile",
    responses=api_error_responses(AUTHENTICATION_PROFILE_NOT_FOUND),
)
async def update_authentication_profile(
    session_id: UUID,
    profile_id: UUID,
    request: UpdateAuthenticationProfileRequest,
    service: FromDishka[SessionService],
) -> AuthenticationProfileResponse:
    profile = await service.update_authentication_profile(
        profile_id,
        session_id=session_id,
        name=request.name,
    )
    return to_authentication_profile_response(profile)


@session_router.delete(
    "/authentication-profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_authentication_profile",
    responses=api_error_responses(AUTHENTICATION_PROFILE_NOT_FOUND),
)
async def delete_authentication_profile(
    profile_id: UUID, service: FromDishka[SessionService]
) -> None:
    await service.delete_authentication_profile(profile_id)


@session_router.put(
    "/sessions/{session_id}/browser-checkpoint",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="mount_session_browser_checkpoint",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        AUTHENTICATION_PROFILE_NOT_FOUND,
        BROWSER_STATE_TRANSFER_FAILED,
    ),
)
async def mount_session_browser_checkpoint(
    session_id: UUID,
    request: MountBrowserCheckpointRequest,
    service: FromDishka[SessionService],
) -> Response:
    checkpoint = await service.get_browser_checkpoint(request.browser_checkpoint_id)
    if checkpoint.authentication_profile_id is not None:
        await service.mount_authentication_profile(
            session_id, checkpoint.authentication_profile_id
        )
    await service.mount_browser(session_id, checkpoint.browser_state)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@session_router.post(
    "/sessions/{session_id}/suspend",
    response_model=SessionResponse,
    operation_id="suspend_session",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        BROWSER_NOT_FOUND,
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
    "/sessions/{session_id}/lease/renew",
    response_model=SessionResponse,
    operation_id="renew_session_lease",
    responses=api_error_responses(
        SESSION_NOT_FOUND,
        SESSION_NOT_ACTIVE,
        BROWSER_NOT_FOUND,
    ),
)
async def renew_session_lease(
    session_id: UUID, service: FromDishka[SessionService]
) -> SessionResponse:
    return to_session_response(await service.renew(session_id))


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
    tunnel: FromDishka[BrowserTunnel],
    lease_keeper: FromDishka[SessionLeaseKeeper],
    routes: FromDishka[BrowserWorkerRoutes],
) -> None:
    session = await _resolve(websocket, lease_keeper, session_id, renew=True)
    if session is None:
        return
    try:
        logger.info(
            "Session tunnel connected session_id=%s owner_id=%s browser_id=%s "
            "slot=%s generation=%s expires_at=%s",
            session_id,
            session.owner_id,
            session.browser_id,
            session.browser.slot.id,
            session.lease_generation,
            session.expires_at.isoformat() if session.expires_at else None,
        )
        await lease_keeper.run(
            session_id,
            tunnel.serve(websocket, routes.cdp_url(session.browser.slot)),
        )
    except (
        LeaseNotFoundException,
        BrowserNotFoundException,
        SessionNotActiveException,
    ):
        logger.info(
            "Session tunnel lost its lease session_id=%s; closing transport",
            session_id,
        )
        await websocket.close(code=1008, reason="Session lease expired")
    finally:
        # State capture is an independent HTTP operation. Keep the lease alive
        # when this transport drops so state can still be read from the worker.
        # DELETE /sessions/{id} or the TTL releases the browser.
        await _log_disconnect(lease_keeper, session_id)


@session_router.websocket("/sessions/{session_id}/screencast")
@inject
async def session_screencast(
    session_id: UUID,
    websocket: WebSocket,
    lease_keeper: FromDishka[SessionLeaseKeeper],
    routes: FromDishka[BrowserWorkerRoutes],
    mode: Annotated[
        ScreencastMode, Query(description="How frames are packaged for the client")
    ] = ScreencastMode.JPEG,
) -> None:
    """Relay the worker's screencast, one fresh subscription per client.

    The worker keeps the state a mode needs per subscription, so every
    connect - and therefore every reconnect - opens with what a client needs to
    start from nothing: a whole frame, a patch covering the whole canvas, or an
    fMP4 init segment ahead of the fragments that depend on it.
    """
    session = await _resolve(websocket, lease_keeper, session_id)
    if session is None:
        return
    name = f"Screencast ({mode})"
    logger.info(
        "%s connected session_id=%s slot=%s",
        name,
        session_id,
        session.browser.slot.id,
    )
    try:
        await proxy_stream(
            websocket, routes.screencast_url(session.browser.slot, mode), name=name
        )
    finally:
        logger.info("%s disconnected session_id=%s", name, session_id)


async def _resolve(
    websocket: WebSocket,
    lease_keeper: SessionLeaseKeeper,
    session_id: UUID,
    *,
    renew: bool = False,
) -> ResolvedSession | None:
    """Look up the live session, closing the socket in session terms when it is gone."""
    try:
        return await lease_keeper.resolve(session_id, renew=renew)
    except LeaseNotFoundException, BrowserNotFoundException, SessionNotActiveException:
        await websocket.accept()
        await websocket.close(code=1008, reason="Session not found")
        return None


async def _log_disconnect(lease_keeper: SessionLeaseKeeper, session_id: UUID) -> None:
    """Say when the unheartbeated lease falls to the reaper, not just that it will."""
    try:
        session = await lease_keeper.resolve(session_id)
    except (
        LeaseNotFoundException,
        BrowserNotFoundException,
        SessionNotActiveException,
    ):
        logger.info(
            "Session tunnel disconnected; lease already gone session_id=%s", session_id
        )
        return
    logger.info(
        "Session tunnel disconnected; no more heartbeats, lease left to its TTL "
        "session_id=%s expires_at=%s reclaim_after=%s",
        session_id,
        session.expires_at.isoformat() if session.expires_at else None,
        session.reclaim_after.isoformat() if session.reclaim_after else None,
    )
