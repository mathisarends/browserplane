from typing import Literal

from fastapi import status

from data_plane.features.browser.state.application.exceptions import (
    BrowserStateFailedException,
    BrowserStateInvalidException,
)
from data_plane.presentation.api_errors import ApiErrorSpec
from data_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


class BrowserStateInvalidError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_STATE_INVALID]


class BrowserStateFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_STATE_FAILED]


BROWSER_STATE_INVALID = ApiErrorSpec(
    exceptions=(BrowserStateInvalidException,),
    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    code=ApiErrorCode.BROWSER_STATE_INVALID,
    response_model=BrowserStateInvalidError,
    description="Browser state cannot be mounted",
)
BROWSER_STATE_FAILED = ApiErrorSpec(
    exceptions=(BrowserStateFailedException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.BROWSER_STATE_FAILED,
    response_model=BrowserStateFailedError,
    description="Browser state operation failed",
)

API_ERRORS = (
    BROWSER_STATE_INVALID,
    BROWSER_STATE_FAILED,
)
