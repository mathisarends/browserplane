from typing import Literal

from fastapi import status

from backend.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserUnavailableException,
)
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.sessions.application.exceptions import (
    NoBrowserAvailableException,
)
from backend.presentation.api_errors import ApiErrorSpec
from backend.presentation.errors import ApiErrorCode, ApiErrorResponse


class SessionNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.SESSION_NOT_FOUND]


class NoBrowserAvailableError(ApiErrorResponse):
    code: Literal[ApiErrorCode.NO_BROWSER_AVAILABLE]


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

API_ERRORS = (SESSION_NOT_FOUND, NO_BROWSER_AVAILABLE)
