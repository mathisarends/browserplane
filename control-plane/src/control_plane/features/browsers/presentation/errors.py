from typing import Literal

from fastapi import status

from control_plane.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserUnavailableException,
)
from control_plane.presentation.api_errors import ApiErrorSpec
from control_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


class BrowserNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_NOT_FOUND]


class BrowserUnavailableError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_UNAVAILABLE]


class BrowserCapacityExhaustedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_CAPACITY_EXHAUSTED]


BROWSER_NOT_FOUND = ApiErrorSpec(
    exceptions=(BrowserNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.BROWSER_NOT_FOUND,
    response_model=BrowserNotFoundError,
    description="Browser not found",
)
BROWSER_UNAVAILABLE = ApiErrorSpec(
    exceptions=(BrowserUnavailableException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.BROWSER_UNAVAILABLE,
    response_model=BrowserUnavailableError,
    description="Browser is not available",
)
BROWSER_CAPACITY_EXHAUSTED = ApiErrorSpec(
    exceptions=(BrowserCapacityExhaustedException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.BROWSER_CAPACITY_EXHAUSTED,
    response_model=BrowserCapacityExhaustedError,
    description="Browser capacity exhausted",
)

API_ERRORS = (
    BROWSER_NOT_FOUND,
    BROWSER_UNAVAILABLE,
    BROWSER_CAPACITY_EXHAUSTED,
)
