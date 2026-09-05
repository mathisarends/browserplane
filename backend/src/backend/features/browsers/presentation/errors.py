from typing import Literal

from fastapi import status

from backend.features.browsers.application.exceptions import (
    BrowserNotFoundException,
    BrowserProvisioningException,
)
from backend.presentation.api_errors import ApiErrorSpec
from backend.presentation.errors import ApiErrorCode, ApiErrorResponse


class BrowserNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_NOT_FOUND]


class BrowserProvisioningFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.BROWSER_PROVISIONING_FAILED]


BROWSER_NOT_FOUND = ApiErrorSpec(
    exceptions=(BrowserNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.BROWSER_NOT_FOUND,
    response_model=BrowserNotFoundError,
    description="Browser not found",
)
# The pool row survives, but the worker behind it did not do as it was told, so
# the caller has to know the process is not in the state the answer implies.
BROWSER_PROVISIONING_FAILED = ApiErrorSpec(
    exceptions=(BrowserProvisioningException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.BROWSER_PROVISIONING_FAILED,
    response_model=BrowserProvisioningFailedError,
    description="The browser could not be provisioned on its worker",
)

API_ERRORS = (BROWSER_NOT_FOUND, BROWSER_PROVISIONING_FAILED)
