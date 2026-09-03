from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    BROWSER_NOT_FOUND = "browser_not_found"
    BROWSER_CAPACITY_EXHAUSTED = "browser_capacity_exhausted"
    BROWSER_STARTUP_FAILED = "browser_startup_failed"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
