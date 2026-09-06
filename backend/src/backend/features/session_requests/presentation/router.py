from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Request, status

from backend.features.session_requests.application.acquisition import (
    OpenSessionCommand,
    ResumeSessionCommand,
    SessionAcquisition,
)
from backend.features.session_requests.application.control_plane import ControlPlane
from backend.features.session_requests.presentation.errors import (
    SESSION_REQUEST_CANCELLED,
    SESSION_REQUEST_CONFLICT,
    SESSION_REQUEST_NOT_FOUND,
    SESSION_REQUEST_TIMED_OUT,
)
from backend.features.session_requests.presentation.schemas import (
    SessionRequestResponse,
)
from backend.features.sessions.presentation.errors import (
    AUTHENTICATION_PROFILE_NOT_FOUND,
    BROWSER_CHECKPOINT_NOT_FOUND,
    SESSION_NOT_ACTIVE,
    SESSION_NOT_FOUND,
    SESSION_NOT_SUSPENDED,
)
from backend.features.sessions.presentation.mapper import (
    to_open_session_response,
    to_session_response,
)
from backend.features.sessions.presentation.schemas import (
    OpenSessionRequest,
    OpenSessionResponse,
    ResumeSessionRequest,
    SessionResponse,
)
from backend.presentation.api_errors import api_error_responses
from backend.presentation.disconnect import while_connected

# Taking a browser is a request that waits; everything a session does
# afterwards is immediate. The two live apart for that reason, not because
# their URLs differ.
acquisition_router = APIRouter(route_class=DishkaRoute, tags=["sessions"])
session_request_router = APIRouter(route_class=DishkaRoute, tags=["session-requests"])

ACQUIRE_ERRORS = (
    SESSION_REQUEST_CONFLICT,
    SESSION_REQUEST_TIMED_OUT,
    SESSION_REQUEST_CANCELLED,
)


@acquisition_router.post(
    "/sessions",
    response_model=OpenSessionResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="open_session",
    responses=api_error_responses(
        *ACQUIRE_ERRORS,
        AUTHENTICATION_PROFILE_NOT_FOUND,
        BROWSER_CHECKPOINT_NOT_FOUND,
    ),
)
async def open_session(
    request: OpenSessionRequest,
    http_request: Request,
    acquisition: FromDishka[SessionAcquisition],
) -> OpenSessionResponse:
    """Queue for a browser and answer once one carries the new session."""
    acquired = await while_connected(
        http_request,
        acquisition.open(
            OpenSessionCommand(
                owner_id=request.owner_id,
                request_id=request.request_id,
                timeout_seconds=request.timeout_seconds,
                test_run_id=request.test_run_id,
                authentication_profile_id=request.authentication_profile_id,
                browser_checkpoint_id=request.browser_checkpoint_id,
            )
        ),
    )
    return to_open_session_response(
        acquired.session, remaining_capacity=acquired.remaining_capacity
    )


@acquisition_router.post(
    "/sessions/{session_id}/resume",
    response_model=SessionResponse,
    operation_id="resume_session",
    responses=api_error_responses(
        *ACQUIRE_ERRORS,
        SESSION_NOT_FOUND,
        SESSION_NOT_SUSPENDED,
        SESSION_NOT_ACTIVE,
        AUTHENTICATION_PROFILE_NOT_FOUND,
        BROWSER_CHECKPOINT_NOT_FOUND,
    ),
)
async def resume_session(
    session_id: UUID,
    request: ResumeSessionRequest,
    http_request: Request,
    acquisition: FromDishka[SessionAcquisition],
) -> SessionResponse:
    """Mount a parked session onto whichever browser becomes free next."""
    session = await while_connected(
        http_request,
        acquisition.resume(
            ResumeSessionCommand(
                session_id=session_id,
                request_id=request.request_id,
                timeout_seconds=request.timeout_seconds,
            )
        ),
    )
    return to_session_response(session)


@session_request_router.get(
    "/session-requests/{request_id}",
    operation_id="get_session_request",
    responses=api_error_responses(SESSION_REQUEST_NOT_FOUND),
)
async def get_session_request(
    request_id: UUID, owner_id: UUID, control: FromDishka[ControlPlane]
) -> SessionRequestResponse:
    """Follow a request that is still waiting, or find out how it ended."""
    return SessionRequestResponse.model_validate(
        await control.get(request_id, owner_id)
    )


@session_request_router.delete(
    "/session-requests/{request_id}",
    operation_id="cancel_session_request",
    responses=api_error_responses(SESSION_REQUEST_NOT_FOUND),
)
async def cancel_session_request(
    request_id: UUID, owner_id: UUID, control: FromDishka[ControlPlane]
) -> SessionRequestResponse:
    """Give up a waiting request. A session it already holds stays open."""
    return SessionRequestResponse.model_validate(
        await control.cancel(request_id, owner_id)
    )
