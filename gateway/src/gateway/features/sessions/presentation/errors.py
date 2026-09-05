from typing import Literal

from fastapi import status

from gateway.features.sessions.application.exceptions import (
    NoBrowserAvailableException,
    SessionExpiredException,
    SessionNotFoundException,
)
from gateway.presentation.api_errors import ApiErrorSpec
from gateway.presentation.errors import ApiErrorCode, ApiErrorResponse


class SessionNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_NOT_FOUND]


class SessionExpiredError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_EXPIRED]


class NoBrowserAvailableError(ApiErrorResponse):
    code: Literal[ApiErrorCode.NO_BROWSER_AVAILABLE]


SESSION_NOT_FOUND = ApiErrorSpec(
    exceptions=(SessionNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.SESSION_NOT_FOUND,
    response_model=SessionNotFoundError,
    description="Session not found",
)
SESSION_EXPIRED = ApiErrorSpec(
    exceptions=(SessionExpiredException,),
    status_code=status.HTTP_410_GONE,
    code=ApiErrorCode.SESSION_EXPIRED,
    response_model=SessionExpiredError,
    description="Session has expired",
)
NO_BROWSER_AVAILABLE = ApiErrorSpec(
    exceptions=(NoBrowserAvailableException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.NO_BROWSER_AVAILABLE,
    response_model=NoBrowserAvailableError,
    description="No browser is currently available",
)

API_ERRORS = (SESSION_NOT_FOUND, SESSION_EXPIRED, NO_BROWSER_AVAILABLE)
