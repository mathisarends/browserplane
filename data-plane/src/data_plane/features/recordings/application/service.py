import asyncio
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from data_plane.features.browsers.application.service import BrowserService
from data_plane.features.recordings.application.exceptions import (
    RecordingAlreadyRunningException,
    RecordingHasSegmentsException,
    RecordingNotCompletedException,
    RecordingNotFoundException,
    RecordingNotRunningException,
)
from data_plane.features.recordings.application.models import (
    RecordedSegment,
    Recording,
    RecordingFile,
    RecordingState,
)
from data_plane.features.recordings.application.ports import ScreenRecorder
from data_plane.infrastructure.bucket import Bucket, BucketObject
from data_plane.settings import DataPlaneSettings

RecorderFactory = Callable[[str, DataPlaneSettings], ScreenRecorder]


@dataclass(slots=True)
class StoredRecording:
    """A recording together with the recorder and directory backing it."""

    recording: Recording
    recorder: ScreenRecorder
    directory: Path


class RecordingService:
    """Own the worker's screen recordings and the segments they produce."""

    def __init__(
        self,
        browsers: BrowserService,
        settings: DataPlaneSettings,
        recorder_factory: RecorderFactory,
        bucket: Bucket,
    ) -> None:
        self._browsers = browsers
        self._settings = settings
        self._recorder_factory = recorder_factory
        self._bucket = bucket
        self._stored: dict[UUID, StoredRecording] = {}
        self._active: UUID | None = None
        self._storage: tempfile.TemporaryDirectory[str] | None = None
        self._lock = asyncio.Lock()

    async def start(self, browser_id: UUID) -> Recording:
        async with self._lock:
            upstream_cdp_url = self._browsers.upstream_cdp_url(browser_id)
            if self._active is not None:
                raise RecordingAlreadyRunningException
            recording = Recording(
                id=uuid4(),
                browser_id=browser_id,
                state=RecordingState.RECORDING,
                started_at=datetime.now(UTC),
            )
            directory = self._storage_path() / str(recording.id)
            directory.mkdir()
            recorder = self._recorder_factory(upstream_cdp_url, self._settings)
            await recorder.start(directory)
            self._stored[recording.id] = StoredRecording(
                recording=recording,
                recorder=recorder,
                directory=directory,
            )
            self._active = recording.id
            return recording

    async def stop(self, browser_id: UUID, recording_id: UUID) -> Recording:
        async with self._lock:
            stored = self._get(browser_id, recording_id)
            if stored.recording.state is not RecordingState.RECORDING:
                raise RecordingNotRunningException
            try:
                segments = await stored.recorder.stop()
                await asyncio.gather(
                    *(
                        self._bucket.put(
                            BucketObject(
                                key=str(
                                    PurePosixPath(
                                        str(browser_id),
                                        str(recording_id),
                                        f"{segment.index}.{segment.format.value}",
                                    )
                                ),
                                path=segment.path,
                                content_type=segment.format.media_type,
                            )
                        )
                        for segment in segments
                    )
                )
            except Exception:
                stored.recording = replace(
                    stored.recording,
                    state=RecordingState.FAILED,
                    stopped_at=datetime.now(UTC),
                )
                raise
            finally:
                self._active = None
            stored.recording = replace(
                stored.recording,
                state=RecordingState.COMPLETED,
                stopped_at=datetime.now(UTC),
                segments=segments,
            )
            return stored.recording

    def get(self, browser_id: UUID, recording_id: UUID) -> Recording:
        return self._get(browser_id, recording_id).recording

    def file(self, browser_id: UUID, recording_id: UUID) -> RecordingFile:
        """Serve a recording that consists of a single file."""
        segments = self._completed_segments(browser_id, recording_id)
        if len(segments) > 1:
            raise RecordingHasSegmentsException
        return _to_file(recording_id, segments[0])

    def segment_file(
        self,
        browser_id: UUID,
        recording_id: UUID,
        index: int,
    ) -> RecordingFile:
        segments = self._completed_segments(browser_id, recording_id)
        if index >= len(segments):
            raise RecordingNotFoundException(f"Recording has no segment {index}")
        return _to_file(recording_id, segments[index])

    async def destroy(self) -> None:
        async with self._lock:
            stored = tuple(self._stored.values())
            self._stored.clear()
            self._active = None
            for entry in stored:
                await entry.recorder.close()
            if self._storage is not None:
                self._storage.cleanup()
                self._storage = None

    def _completed_segments(
        self,
        browser_id: UUID,
        recording_id: UUID,
    ) -> tuple[RecordedSegment, ...]:
        recording = self._get(browser_id, recording_id).recording
        if recording.state is not RecordingState.COMPLETED or not recording.segments:
            raise RecordingNotCompletedException
        return recording.segments

    def _get(self, browser_id: UUID, recording_id: UUID) -> StoredRecording:
        stored = self._stored.get(recording_id)
        if stored is None or stored.recording.browser_id != browser_id:
            raise RecordingNotFoundException
        return stored

    def _storage_path(self) -> Path:
        if self._storage is None:
            self._storage = tempfile.TemporaryDirectory(
                prefix="data-plane-recordings-", ignore_cleanup_errors=True
            )
        return Path(self._storage.name)


def _to_file(recording_id: UUID, segment: RecordedSegment) -> RecordingFile:
    return RecordingFile(
        path=segment.path,
        media_type=segment.format.media_type,
        filename=f"{recording_id}-{segment.index}.{segment.format.value}",
    )
