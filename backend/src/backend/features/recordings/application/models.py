from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RecordingState(StrEnum):
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Recording:
    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None
    size_bytes: int | None
