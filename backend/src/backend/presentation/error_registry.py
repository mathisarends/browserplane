from fastapi_canon import ErrorRegistry

from backend.features.browsers.presentation.errors import ERRORS as BROWSER_ERRORS
from backend.features.recordings.presentation.errors import ERRORS as RECORDING_ERRORS
from backend.features.session_requests.presentation.errors import (
    ERRORS as SESSION_REQUEST_ERRORS,
)
from backend.features.sessions.presentation.errors import ERRORS as SESSION_ERRORS

API_ERRORS = ErrorRegistry.merge(
    BROWSER_ERRORS,
    SESSION_ERRORS,
    SESSION_REQUEST_ERRORS,
    RECORDING_ERRORS,
    name="backend-api",
)
