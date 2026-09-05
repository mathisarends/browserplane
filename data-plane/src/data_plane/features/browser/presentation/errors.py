from typing import Literal

from fastapi import status

from data_plane.features.browser.application.exceptions import (
    BrowserAlreadyRunningException,
    BrowserNotFoundException,
    BrowserStartupException,
)
from data_plane.presentation.api_errors import ApiErrorSpec
from data_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


class BrowserNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_NOT_FOUND]


class BrowserAlreadyRunningError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_ALREADY_RUNNING]


class BrowserStartupFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_STARTUP_FAILED]


BROWSER_NOT_FOUND = ApiErrorSpec(
    exceptions=(BrowserNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.BROWSER_NOT_FOUND,
    response_model=BrowserNotFoundError,
    description="Browser not found",
)
BROWSER_ALREADY_RUNNING = ApiErrorSpec(
    exceptions=(BrowserAlreadyRunningException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.BROWSER_ALREADY_RUNNING,
    response_model=BrowserAlreadyRunningError,
    description="Worker already runs a browser",
)
BROWSER_STARTUP_FAILED = ApiErrorSpec(
    exceptions=(BrowserStartupException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.BROWSER_STARTUP_FAILED,
    response_model=BrowserStartupFailedError,
    description="Browser failed to start",
)

API_ERRORS = (
    BROWSER_NOT_FOUND,
    BROWSER_ALREADY_RUNNING,
    BROWSER_STARTUP_FAILED,
)
