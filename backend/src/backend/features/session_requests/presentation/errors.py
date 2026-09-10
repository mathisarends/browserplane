from uuid import UUID

from fastapi import status
from fastapi_canon import Error, ErrorRegistry
from pydantic import BaseModel

from backend.features.session_requests.domain import (
    SessionRequestCancelledException,
    SessionRequestConflictException,
    SessionRequestNotFoundException,
    SessionRequestTimedOutException,
)


class SessionRequestExtension(BaseModel):
    request_id: UUID


def _request_extension(error: Exception) -> dict[str, UUID]:
    request_id = getattr(error, "details", {}).get("request_id")
    return {"request_id": request_id}


# A request that belongs to someone else answers like one that never existed,
# so an id cannot be probed for.
SESSION_REQUEST_NOT_FOUND = Error(
    SessionRequestNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="session_request_not_found",
    title="Session request not found",
    detail=str,
)
SESSION_REQUEST_CONFLICT = Error(
    SessionRequestConflictException,
    status=status.HTTP_409_CONFLICT,
    code="session_request_conflict",
    title="Request ID already belongs to different input",
    detail=str,
)
SESSION_REQUEST_TIMED_OUT = Error(
    SessionRequestTimedOutException,
    status=status.HTTP_408_REQUEST_TIMEOUT,
    code="session_request_timed_out",
    title="No browser became available before the deadline",
    detail=str,
    extensions_model=SessionRequestExtension,
    extensions=_request_extension,
)
SESSION_REQUEST_CANCELLED = Error(
    SessionRequestCancelledException,
    status=status.HTTP_409_CONFLICT,
    code="session_request_cancelled",
    title="The session request was cancelled",
    detail=str,
    extensions_model=SessionRequestExtension,
    extensions=_request_extension,
)

API_ERRORS = (
    SESSION_REQUEST_NOT_FOUND,
    SESSION_REQUEST_CONFLICT,
    SESSION_REQUEST_TIMED_OUT,
    SESSION_REQUEST_CANCELLED,
)
ERRORS = ErrorRegistry(name="session_requests", errors=API_ERRORS)
