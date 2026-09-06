import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
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
class ActiveRecording:
    """The single recorder that currently owns live browser resources."""

    id: UUID
    recorder: ScreenRecorder


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
        # Completed and failed recordings remain queryable until the worker is reset.
        # Only _active_recording owns a live recorder; recordings are not segments.
        self._recordings_by_id: dict[UUID, Recording] = {}
        self._active_recording: ActiveRecording | None = None
        self._lock = asyncio.Lock()

    async def start(self, browser_id: UUID) -> Recording:
        async with self._lock:
            upstream_cdp_url = self._browsers.upstream_cdp_url(browser_id)
            if self._active_recording is not None:
                raise RecordingAlreadyRunningException
            recording = Recording(
                id=uuid4(),
                browser_id=browser_id,
                state=RecordingState.RECORDING,
                started_at=datetime.now(UTC),
            )
            directory = self._workspace.create_recording_directory(recording.id)
            recorder = self._recorder_factory(upstream_cdp_url)
            await recorder.start(directory)
            self._recordings_by_id[recording.id] = recording
            self._active_recording = ActiveRecording(
                id=recording.id,
                recorder=recorder,
            )
            return recording

    async def stop(self, browser_id: UUID, recording_id: UUID) -> Recording:
        async with self._lock:
            recording = self._get(browser_id, recording_id)
            active = self._active_recording
            if (
                recording.state is not RecordingState.RECORDING
                or active is None
                or active.id != recording_id
            ):
                raise RecordingNotRunningException
            try:
                video = await active.recorder.stop()
            except Exception as stop_error:
                self._recordings_by_id[recording_id] = replace(
                    recording,
                    state=RecordingState.FAILED,
                    stopped_at=datetime.now(UTC),
                )
                try:
                    await active.recorder.close()
                except Exception as close_error:
                    raise ExceptionGroup(
                        "Could not stop and close recording",
                        [stop_error, close_error],
                    ) from stop_error
                raise
            finally:
                self._active_recording = None
            completed = replace(
                recording,
                state=RecordingState.COMPLETED,
                stopped_at=datetime.now(UTC),
                video=video,
            )
            self._recordings_by_id[recording_id] = completed
            return completed

    def get(self, browser_id: UUID, recording_id: UUID) -> Recording:
        return self._get(browser_id, recording_id)

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

    async def release(self) -> None:
        """Close the active recorder and forget the in-memory history.

        The worker-level release owns deletion of files through ``Workspace.clear``.
        """
        async with self._lock:
            active, self._active_recording = self._active_recording, None
            self._recordings_by_id.clear()
            if active is not None:
                await active.recorder.close()

    def _completed_video(
        self,
        browser_id: UUID,
        recording_id: UUID,
    ) -> RecordedVideo:
        recording = self._get(browser_id, recording_id)
        if recording.state is not RecordingState.COMPLETED or recording.video is None:
            raise RecordingNotCompletedException
        return recording.video

    def _get(self, browser_id: UUID, recording_id: UUID) -> Recording:
        recording = self._recordings_by_id.get(recording_id)
        if recording is None or recording.browser_id != browser_id:
            raise RecordingNotFoundException
        return recording


def _to_file(recording_id: UUID, video: RecordedVideo) -> RecordingFile:
    return RecordingFile(
        path=video.path,
        media_type=video.format.media_type,
        filename=f"{recording_id}-0.{video.format.value}",
    )
