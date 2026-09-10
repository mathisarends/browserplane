from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from browser_worker.features.state.application.exceptions import (
    BrowserStateFailedException,
    BrowserStateInvalidException,
)

BROWSER_STATE_INVALID = Error(
    BrowserStateInvalidException,
    status=status.HTTP_422_UNPROCESSABLE_CONTENT,
    code="browser_state_invalid",
    title="Browser state cannot be mounted",
    detail=str,
)
BROWSER_STATE_FAILED = Error(
    BrowserStateFailedException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="browser_state_failed",
    title="Browser state operation failed",
    detail=str,
)

API_ERRORS = (BROWSER_STATE_INVALID, BROWSER_STATE_FAILED)
ERRORS = ErrorRegistry(name="state", errors=API_ERRORS)
