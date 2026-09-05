from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from browser_worker.features.recordings.application.models import (
    RecordingFormat,
    RecordingState,
)


class RecordingSegmentResponse(BaseModel):
    """One video file, covering the time a single tab was the active one."""

    index: int
    target_id: str
    size_bytes: int
    format: RecordingFormat
    started_at: datetime
    stopped_at: datetime


class RecordingResponse(BaseModel):
    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    size_bytes: int | None = None
    segments: list[RecordingSegmentResponse] = []
