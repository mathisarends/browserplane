from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.features.recordings.application.models import (
    RecordingFormat,
    RecordingState,
)


class RecordingSegmentResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    index: int
    target_id: str
    size_bytes: int
    format: RecordingFormat
    started_at: datetime
    stopped_at: datetime


class RecordingResponse(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    size_bytes: int | None = None
    segments: list[RecordingSegmentResponse] = []
