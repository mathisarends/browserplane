from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from backend.features.browsers.application.exceptions import BrowserUnavailableException
from backend.features.sessions.application.exceptions import (
    AuthenticationProfileNotFoundException,
    BrowserCheckpointNotFoundException,
    BrowserStateTransferException,
    DownloadNotFoundException,
    SessionNotActiveException,
    SessionNotFoundException,
    SessionNotSuspendedException,
)

SESSION_NOT_FOUND = Error(
    SessionNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="session_not_found",
    title="Session not found",
    detail=str,
)
NO_BROWSER_AVAILABLE = Error(
    BrowserUnavailableException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="no_browser_available",
    title="No browser is currently available",
    detail=str,
)
SESSION_NOT_ACTIVE = Error(
    SessionNotActiveException,
    status=status.HTTP_409_CONFLICT,
    code="session_not_active",
    title="Session is suspended and holds no browser",
    detail=str,
)
SESSION_NOT_SUSPENDED = Error(
    SessionNotSuspendedException,
    status=status.HTTP_409_CONFLICT,
    code="session_not_suspended",
    title="Session is not suspended",
    detail=str,
)
BROWSER_STATE_TRANSFER_FAILED = Error(
    BrowserStateTransferException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="browser_state_transfer_failed",
    title="Could not transfer the browser state",
    detail=str,
)
DOWNLOAD_NOT_FOUND = Error(
    DownloadNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="download_not_found",
    title="Download not found",
    detail=str,
)
AUTHENTICATION_PROFILE_NOT_FOUND = Error(
    AuthenticationProfileNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="authentication_profile_not_found",
    title="Authentication profile not found",
    detail=str,
)
BROWSER_CHECKPOINT_NOT_FOUND = Error(
    BrowserCheckpointNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="browser_checkpoint_not_found",
    title="Browser checkpoint not found",
    detail=str,
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
ERRORS = ErrorRegistry(name="sessions", errors=API_ERRORS)
