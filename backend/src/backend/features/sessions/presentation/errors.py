from typing import Literal

from fastapi import status

from backend.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserUnavailableException,
)
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.exceptions import (
    BrowserStateTransferException,
    NoBrowserAvailableException,
    SessionNotActiveException,
    SessionNotSuspendedException,
)
from backend.presentation.api_errors import ApiErrorSpec
from backend.presentation.errors import ApiErrorCode, ApiErrorResponse


class SessionNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_NOT_FOUND]


class NoBrowserAvailableError(ApiErrorResponse):
    code: Literal[ApiErrorCode.NO_BROWSER_AVAILABLE]


class SessionNotActiveError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_NOT_ACTIVE]


class SessionNotSuspendedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_NOT_SUSPENDED]


class BrowserStateTransferFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_STATE_TRANSFER_FAILED]


# An expired lease is dropped on access, so it reaches the edge as "not found",
# and a lease whose browser vanished leaves nothing to hand the client either.
SESSION_NOT_FOUND = ApiErrorSpec(
    exceptions=(LeaseNotFoundException, BrowserNotFoundException),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.SESSION_NOT_FOUND,
    response_model=SessionNotFoundError,
    description="Session not found",
)
# The pool being empty and losing the race for the browser we picked are the
# same situation to a client: try again later.
NO_BROWSER_AVAILABLE = ApiErrorSpec(
    exceptions=(
        NoBrowserAvailableException,
        BrowserUnavailableException,
        BrowserCapacityExhaustedException,
    ),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.NO_BROWSER_AVAILABLE,
    response_model=NoBrowserAvailableError,
    description="No browser is currently available",
)

SESSION_NOT_ACTIVE = ApiErrorSpec(
    exceptions=(SessionNotActiveException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.SESSION_NOT_ACTIVE,
    response_model=SessionNotActiveError,
    description="Session is suspended and holds no browser",
)
SESSION_NOT_SUSPENDED = ApiErrorSpec(
    exceptions=(SessionNotSuspendedException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.SESSION_NOT_SUSPENDED,
    response_model=SessionNotSuspendedError,
    description="Session is not suspended",
)
# Suspending without a readable state would hand back a browser we can never
# reconstruct, so the caller has to know it did not happen.
BROWSER_STATE_TRANSFER_FAILED = ApiErrorSpec(
    exceptions=(BrowserStateTransferException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.BROWSER_STATE_TRANSFER_FAILED,
    response_model=BrowserStateTransferFailedError,
    description="Could not transfer the browser state",
)

API_ERRORS = (
    SESSION_NOT_FOUND,
    NO_BROWSER_AVAILABLE,
    SESSION_NOT_ACTIVE,
    SESSION_NOT_SUSPENDED,
    BROWSER_STATE_TRANSFER_FAILED,
)
