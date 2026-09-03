from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    BROWSER_NOT_FOUND = "browser_not_found"
    BROWSER_UNAVAILABLE = "browser_unavailable"
    BROWSER_CAPACITY_EXHAUSTED = "browser_capacity_exhausted"
    LEASE_NOT_FOUND = "lease_not_found"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
