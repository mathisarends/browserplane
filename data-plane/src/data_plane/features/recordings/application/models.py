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
    """Container Chromium wrote the recording in."""

    WEBM = "webm"
    MP4 = "mp4"

    @property
    def media_type(self) -> str:
        return f"video/{self.value}"


@dataclass(frozen=True, slots=True)
class RecordedSegment:
    """One video file, covering the time a single tab was the active one.

    Chromium records a fixed page target, so following the active tab means
    ending a segment and starting the next one whenever the shown tab changes.
    """

    index: int
    target_id: str
    path: Path
    size_bytes: int
    format: RecordingFormat
    started_at: datetime
    stopped_at: datetime


@dataclass(frozen=True, slots=True)
class Recording:
    """A screen recording of the worker's browser."""

    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    segments: tuple[RecordedSegment, ...] = ()

    @property
    def size_bytes(self) -> int | None:
        if self.state is not RecordingState.COMPLETED:
            return None
        return sum(segment.size_bytes for segment in self.segments)


@dataclass(frozen=True, slots=True)
class RecordingFile:
    """A stored segment ready to be served to a client."""

    path: Path
    media_type: str
    filename: str
