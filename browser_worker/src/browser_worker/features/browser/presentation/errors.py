from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from browser_worker.features.browser.application.exceptions import (
    BrowserAlreadyRunningException,
    BrowserNotFoundException,
    BrowserStartupException,
)

BROWSER_NOT_FOUND = Error(
    BrowserNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="browser_not_found",
    title="Browser not found",
    detail=str,
)
BROWSER_ALREADY_RUNNING = Error(
    BrowserAlreadyRunningException,
    status=status.HTTP_409_CONFLICT,
    code="browser_already_running",
    title="Worker already runs a browser",
    detail=str,
)
BROWSER_STARTUP_FAILED = Error(
    BrowserStartupException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="browser_startup_failed",
    title="Browser failed to start",
    detail=str,
)

API_ERRORS = (
    BROWSER_NOT_FOUND,
    BROWSER_ALREADY_RUNNING,
    BROWSER_STARTUP_FAILED,
)
ERRORS = ErrorRegistry(name="browser", errors=API_ERRORS)
