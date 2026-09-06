from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    SESSION_NOT_FOUND = "session_not_found"
    NO_BROWSER_AVAILABLE = "no_browser_available"
    SESSION_NOT_ACTIVE = "session_not_active"
    SESSION_NOT_SUSPENDED = "session_not_suspended"
    BROWSER_STATE_TRANSFER_FAILED = "browser_state_transfer_failed"
    DOWNLOAD_NOT_FOUND = "download_not_found"
    BROWSER_NOT_FOUND = "browser_not_found"
    BROWSER_PROVISIONING_FAILED = "browser_provisioning_failed"
    RECORDING_NOT_FOUND = "recording_not_found"
    RECORDING_ALREADY_EXISTS = "recording_already_exists"
    RECORDING_NOT_RUNNING = "recording_not_running"
    RECORDING_TRANSFER_FAILED = "recording_transfer_failed"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
