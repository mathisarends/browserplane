from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    SESSION_NOT_FOUND = "session_not_found"
    NO_BROWSER_AVAILABLE = "no_browser_available"
    SESSION_NOT_ACTIVE = "session_not_active"
    SESSION_NOT_SUSPENDED = "session_not_suspended"
    BROWSER_STATE_TRANSFER_FAILED = "browser_state_transfer_failed"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
