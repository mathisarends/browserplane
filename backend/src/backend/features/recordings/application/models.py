from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RecordingFormat(StrEnum):
    WEBM = "webm"
    MP4 = "mp4"


class RecordingState(StrEnum):
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RecordingSegment:
    index: int
    target_id: str
    size_bytes: int
    format: RecordingFormat
    started_at: datetime
    stopped_at: datetime


@dataclass(frozen=True, slots=True)
class Recording:
    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None
    size_bytes: int | None
    segments: tuple[RecordingSegment, ...]
