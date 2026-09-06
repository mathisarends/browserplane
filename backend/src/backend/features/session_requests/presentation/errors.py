from typing import Literal
from uuid import UUID

from fastapi import status

from backend.features.session_requests.domain import (
    SessionRequestCancelledException,
    SessionRequestConflictException,
    SessionRequestNotFoundException,
    SessionRequestTimedOutException,
)
from backend.presentation.api_errors import ApiErrorSpec
from backend.presentation.errors import ApiErrorCode, ApiErrorResponse


class SessionRequestNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_REQUEST_NOT_FOUND]


class SessionRequestConflictError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_REQUEST_CONFLICT]


class SessionRequestTimedOutError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_REQUEST_TIMED_OUT]
    request_id: UUID


class SessionRequestCancelledError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_REQUEST_CANCELLED]
    request_id: UUID


# A request that belongs to someone else answers like one that never existed,
# so an id cannot be probed for.
SESSION_REQUEST_NOT_FOUND = ApiErrorSpec(
    exceptions=(SessionRequestNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.SESSION_REQUEST_NOT_FOUND,
    response_model=SessionRequestNotFoundError,
    description="Session request not found",
)
SESSION_REQUEST_CONFLICT = ApiErrorSpec(
    exceptions=(SessionRequestConflictException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.SESSION_REQUEST_CONFLICT,
    response_model=SessionRequestConflictError,
    description="Request ID already belongs to different input",
)
# The deadline passed rather than anything going wrong, so the caller may ask
# again. Both endings name the request, which is what a retry needs.
SESSION_REQUEST_TIMED_OUT = ApiErrorSpec(
    exceptions=(SessionRequestTimedOutException,),
    status_code=status.HTTP_408_REQUEST_TIMEOUT,
    code=ApiErrorCode.SESSION_REQUEST_TIMED_OUT,
    response_model=SessionRequestTimedOutError,
    description="No browser became available before the deadline",
)
SESSION_REQUEST_CANCELLED = ApiErrorSpec(
    exceptions=(SessionRequestCancelledException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.SESSION_REQUEST_CANCELLED,
    response_model=SessionRequestCancelledError,
    description="The session request was cancelled",
)

API_ERRORS = (
    SESSION_REQUEST_NOT_FOUND,
    SESSION_REQUEST_CONFLICT,
    SESSION_REQUEST_TIMED_OUT,
    SESSION_REQUEST_CANCELLED,
)
