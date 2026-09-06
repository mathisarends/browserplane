from typing import Literal

from fastapi import status

from backend.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserUnavailableException,
)
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.exceptions import (
    AuthenticationProfileNotFoundException,
    BrowserCheckpointNotFoundException,
    BrowserStateTransferException,
    DownloadNotFoundException,
    SessionNotActiveException,
    SessionNotFoundException,
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


class DownloadNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.DOWNLOAD_NOT_FOUND]


class AuthenticationProfileNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.AUTHENTICATION_PROFILE_NOT_FOUND]


class BrowserCheckpointNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_CHECKPOINT_NOT_FOUND]


# A lease that expired or crossed its reclaim fence reaches the edge as "not found".
# A lease whose browser vanished answers with the pool's own BROWSER_NOT_FOUND.
SESSION_NOT_FOUND = ApiErrorSpec(
    exceptions=(LeaseNotFoundException, SessionNotFoundException),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.SESSION_NOT_FOUND,
    response_model=SessionNotFoundError,
    description="Session not found",
)
# An empty pool no longer reaches a caller as a failure: they queue for
# capacity instead. What remains is losing the race for a browser that was
# free a moment ago, which is the same situation to a client: try again later.
NO_BROWSER_AVAILABLE = ApiErrorSpec(
    exceptions=(
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
DOWNLOAD_NOT_FOUND = ApiErrorSpec(
    exceptions=(DownloadNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.DOWNLOAD_NOT_FOUND,
    response_model=DownloadNotFoundError,
    description="Download not found",
)
AUTHENTICATION_PROFILE_NOT_FOUND = ApiErrorSpec(
    exceptions=(AuthenticationProfileNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.AUTHENTICATION_PROFILE_NOT_FOUND,
    response_model=AuthenticationProfileNotFoundError,
    description="Authentication profile not found",
)
BROWSER_CHECKPOINT_NOT_FOUND = ApiErrorSpec(
    exceptions=(BrowserCheckpointNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.BROWSER_CHECKPOINT_NOT_FOUND,
    response_model=BrowserCheckpointNotFoundError,
    description="Browser checkpoint not found",
)

API_ERRORS = (
    SESSION_NOT_FOUND,
    NO_BROWSER_AVAILABLE,
    SESSION_NOT_ACTIVE,
    SESSION_NOT_SUSPENDED,
    BROWSER_STATE_TRANSFER_FAILED,
    DOWNLOAD_NOT_FOUND,
    AUTHENTICATION_PROFILE_NOT_FOUND,
    BROWSER_CHECKPOINT_NOT_FOUND,
)
