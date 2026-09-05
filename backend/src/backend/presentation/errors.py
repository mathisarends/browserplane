from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    SESSION_NOT_FOUND = "session_not_found"
    NO_BROWSER_AVAILABLE = "no_browser_available"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
