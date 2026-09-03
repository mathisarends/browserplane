from enum import StrEnum

from pydantic import BaseModel


class ApiErrorCode(StrEnum):
    BROWSER_NOT_FOUND = "browser_not_found"
    BROWSER_ALREADY_RUNNING = "browser_already_running"
    BROWSER_STARTUP_FAILED = "browser_startup_failed"
    RECORDING_NOT_FOUND = "recording_not_found"
    RECORDING_ALREADY_RUNNING = "recording_already_running"
    RECORDING_NOT_RUNNING = "recording_not_running"
    RECORDING_NOT_COMPLETED = "recording_not_completed"
    RECORDING_HAS_SEGMENTS = "recording_has_segments"
    RECORDING_FAILED = "recording_failed"


class ApiErrorResponse(BaseModel):
    code: ApiErrorCode
    message: str
