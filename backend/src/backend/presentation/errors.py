from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_EXPIRED = "session_expired"
    NO_BROWSER_AVAILABLE = "no_browser_available"
    UPSTREAM_UNAVAILABLE = "upstream_unavailable"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
