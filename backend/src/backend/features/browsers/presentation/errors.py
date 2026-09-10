from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from backend.features.browsers.application.exceptions import (
    BrowserNotFoundException,
    BrowserProvisioningException,
)

BROWSER_NOT_FOUND = Error(
    BrowserNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="browser_not_found",
    title="Browser not found",
    detail=str,
)
# The pool row survives, but the worker behind it did not do as it was told, so
# the caller has to know the process is not in the state the answer implies.
BROWSER_PROVISIONING_FAILED = Error(
    BrowserProvisioningException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="browser_provisioning_failed",
    title="The browser could not be provisioned on its worker",
    detail=str,
)

API_ERRORS = (BROWSER_NOT_FOUND, BROWSER_PROVISIONING_FAILED)
ERRORS = ErrorRegistry(name="browsers", errors=API_ERRORS)
