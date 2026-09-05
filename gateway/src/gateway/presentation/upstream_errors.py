from typing import Literal

from fastapi import status

from gateway.exceptions import UpstreamUnavailableException
from gateway.presentation.api_errors import ApiErrorSpec
from gateway.presentation.errors import ApiErrorCode, ApiErrorResponse


class UpstreamUnavailableError(ApiErrorResponse):
    code: Literal[ApiErrorCode.UPSTREAM_UNAVAILABLE]


UPSTREAM_UNAVAILABLE = ApiErrorSpec(
    exceptions=(UpstreamUnavailableException,),
    status_code=status.HTTP_502_BAD_GATEWAY,
    code=ApiErrorCode.UPSTREAM_UNAVAILABLE,
    response_model=UpstreamUnavailableError,
    description="An internal plane could not be reached",
)

API_ERRORS = (UPSTREAM_UNAVAILABLE,)
