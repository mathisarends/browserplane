from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID


class RecordingState(StrEnum):
    """Lifecycle of a screen recording as seen by API clients."""

    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"


class RecordingFormat(StrEnum):
    """Container used for a completed recording."""

    WEBM = "webm"
    MP4 = "mp4"

    @property
    def media_type(self) -> str:
        return f"video/{self.value}"


@dataclass(frozen=True, slots=True)
class RecordedVideo:
    path: Path
    size_bytes: int
    format: RecordingFormat


@dataclass(frozen=True, slots=True)
class Recording:
    """A screen recording of the worker's browser."""

    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    video: RecordedVideo | None = None

    @property
    def size_bytes(self) -> int | None:
        return self.video.size_bytes if self.video is not None else None


@dataclass(frozen=True, slots=True)
class RecordingFile:
    path: Path
    media_type: str
    filename: str
