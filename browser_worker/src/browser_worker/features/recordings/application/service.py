import asyncio
import shutil
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.recordings.application.exceptions import (
    RecordingAlreadyRunningException,
    RecordingNotCompletedException,
    RecordingNotFoundException,
    RecordingNotRunningException,
)
from browser_worker.features.recordings.application.models import (
    RecordedVideo,
    Recording,
    RecordingFile,
    RecordingState,
)
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.workspace.application.workspace import Workspace

RecorderFactory = Callable[[str], ScreenRecorder]


@dataclass(slots=True)
class StoredRecording:
    """A recording together with the recorder and directory backing it."""

    recording: Recording
    recorder: ScreenRecorder
    directory: Path


class RecordingService:
    def __init__(
        self,
        browsers: BrowserService,
        workspace: Workspace,
        recorder_factory: RecorderFactory,
    ) -> None:
        self._browsers = browsers
        self._workspace = workspace
        self._recorder_factory = recorder_factory
        self._stored: dict[UUID, StoredRecording] = {}
        self._active: UUID | None = None
        self._storage: Path | None = None
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
            recorder = self._recorder_factory(upstream_cdp_url)
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
                video = await stored.recorder.stop()
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
                video=video,
            )
            return stored.recording

    def get(self, browser_id: UUID, recording_id: UUID) -> Recording:
        return self._get(browser_id, recording_id).recording

    def file(self, browser_id: UUID, recording_id: UUID) -> RecordingFile:
        return _to_file(recording_id, self._completed_video(browser_id, recording_id))

    def segment_file(
        self,
        browser_id: UUID,
        recording_id: UUID,
        index: int,
    ) -> RecordingFile:
        if index != 0:
            raise RecordingNotFoundException(f"Recording has no segment {index}")
        return self.file(browser_id, recording_id)

    async def destroy(self) -> None:
        async with self._lock:
            stored = tuple(self._stored.values())
            self._stored.clear()
            self._active = None
            for entry in stored:
                await entry.recorder.close()
                shutil.rmtree(entry.directory, ignore_errors=True)
            if self._storage is not None:
                self._storage = None

    def _completed_video(
        self,
        browser_id: UUID,
        recording_id: UUID,
    ) -> RecordedVideo:
        recording = self._get(browser_id, recording_id).recording
        if recording.state is not RecordingState.COMPLETED or recording.video is None:
            raise RecordingNotCompletedException
        return recording.video

    def _get(self, browser_id: UUID, recording_id: UUID) -> StoredRecording:
        stored = self._stored.get(recording_id)
        if stored is None or stored.recording.browser_id != browser_id:
            raise RecordingNotFoundException
        return stored

    def _storage_path(self) -> Path:
        if self._storage is None:
            self._storage = self._workspace.recordings
            self._storage.mkdir(parents=True, exist_ok=True)
        return self._storage


def _to_file(recording_id: UUID, video: RecordedVideo) -> RecordingFile:
    return RecordingFile(
        path=video.path,
        media_type=video.format.media_type,
        filename=f"{recording_id}-0.{video.format.value}",
    )
