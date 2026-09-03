# Generated from data_plane-openapi.json. Do not edit manually.

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class BrowserAlreadyRunningError(BaseModel):
    code: Literal["browser_already_running"]
    message: str


class BrowserNotFoundError(BaseModel):
    code: Literal["browser_not_found"]
    message: str


class BrowserResponse(BaseModel):
    id: UUID
    cdp_url: str


class BrowserStartupFailedError(BaseModel):
    code: Literal["browser_startup_failed"]
    message: str


class CreateBrowserRequest(BaseModel):
    id: UUID


class ValidationError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any | None = None
    ctx: dict[str, Any] | None = None


class HTTPValidationError(BaseModel):
    detail: list[ValidationError] | None = None


class HealthStatus(StrEnum):
    OK = "ok"


class HealthResponse(BaseModel):
    status: HealthStatus


class RecordingAlreadyRunningError(BaseModel):
    code: Literal["recording_already_running"]
    message: str


class RecordingFailedError(BaseModel):
    code: Literal["recording_failed"]
    message: str


class RecordingFormat(StrEnum):
    WEBM = "webm"
    MP4 = "mp4"


class RecordingHasSegmentsError(BaseModel):
    code: Literal["recording_has_segments"]
    message: str


class RecordingNotCompletedError(BaseModel):
    code: Literal["recording_not_completed"]
    message: str


class RecordingNotFoundError(BaseModel):
    code: Literal["recording_not_found"]
    message: str


class RecordingNotRunningError(BaseModel):
    code: Literal["recording_not_running"]
    message: str


class RecordingSegmentResponse(BaseModel):
    index: int
    target_id: str
    size_bytes: int
    format: RecordingFormat
    started_at: datetime
    stopped_at: datetime


class RecordingState(StrEnum):
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"


class RecordingResponse(BaseModel):
    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    size_bytes: int | None = None
    segments: list[RecordingSegmentResponse] = []
