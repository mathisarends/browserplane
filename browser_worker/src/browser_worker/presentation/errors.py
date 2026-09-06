from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    BROWSER_NOT_FOUND = "browser_not_found"
    BROWSER_ALREADY_RUNNING = "browser_already_running"
    BROWSER_STARTUP_FAILED = "browser_startup_failed"
    BROWSER_STATE_INVALID = "browser_state_invalid"
    BROWSER_STATE_FAILED = "browser_state_failed"
    DOWNLOAD_NOT_FOUND = "download_not_found"
    RECORDING_NOT_FOUND = "recording_not_found"
    RECORDING_ALREADY_EXISTS = "recording_already_exists"
    RECORDING_NOT_RUNNING = "recording_not_running"
    RECORDING_NOT_COMPLETED = "recording_not_completed"
    RECORDING_FAILED = "recording_failed"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
