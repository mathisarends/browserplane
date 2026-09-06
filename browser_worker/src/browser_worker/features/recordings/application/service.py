import asyncio
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.recordings.application.exceptions import (
    RecordingAlreadyExistsException,
    RecordingNotCompletedException,
    RecordingNotFoundException,
    RecordingNotRunningException,
)
from browser_worker.features.recordings.application.models import (
    Recording,
    RecordingFile,
    RecordingState,
)
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.workspace.application.workspace import Workspace

RecorderFactory = Callable[[str], ScreenRecorder]


class RecordingService:
    """Manage the session's single recording and optional completed video."""

    def __init__(
        self,
        browsers: BrowserService,
        workspace: Workspace,
        recorder_factory: RecorderFactory,
    ) -> None:
        self._browsers = browsers
        self._workspace = workspace
        self._recorder_factory = recorder_factory
        self._recording: Recording | None = None
        self._recorder: ScreenRecorder | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> Recording:
        async with self._lock:
            upstream_cdp_url = self._browsers.upstream_cdp_url()
            if (
                self._recording is not None
                and self._recording.state is not RecordingState.FAILED
            ):
                raise RecordingAlreadyExistsException
            recording = Recording(
                id=uuid4(),
                state=RecordingState.RECORDING,
                started_at=datetime.now(UTC),
            )
            directory = self._workspace.create_recording_directory(recording.id)
            recorder = self._recorder_factory(upstream_cdp_url)
            await recorder.start(directory)
            self._recording = recording
            self._recorder = recorder
            return recording

    async def stop(self, recording_id: UUID) -> Recording:
        async with self._lock:
            recording = self.get(recording_id)
            recorder = self._recorder
            if recording.state is not RecordingState.RECORDING or recorder is None:
                raise RecordingNotRunningException
            try:
                video = await recorder.stop()
            except Exception as stop_error:
                self._recording = replace(
                    recording,
                    state=RecordingState.FAILED,
                    stopped_at=datetime.now(UTC),
                )
                try:
                    await recorder.close()
                except Exception as close_error:
                    raise ExceptionGroup(
                        "Could not stop and close recording",
                        [stop_error, close_error],
                    ) from stop_error
                raise
            finally:
                self._recorder = None
            completed = replace(
                recording,
                state=RecordingState.COMPLETED,
                stopped_at=datetime.now(UTC),
                video=video,
            )
            self._recording = completed
            return completed

    def get(self, recording_id: UUID) -> Recording:
        recording = self._recording
        if recording is None or recording.id != recording_id:
            raise RecordingNotFoundException
        return recording

    def file(self, recording_id: UUID) -> RecordingFile:
        recording = self.get(recording_id)
        video = recording.video
        if recording.state is not RecordingState.COMPLETED or video is None:
            raise RecordingNotCompletedException
        return RecordingFile(
            path=video.path,
            media_type=video.format.media_type,
            filename=f"{recording_id}.{video.format.value}",
        )

    async def release(self) -> None:
        """Close the active recorder and forget the in-memory history.

        The worker-level release owns deletion of files through ``Workspace.clear``.
        """
        async with self._lock:
            recorder, self._recorder = self._recorder, None
            self._recording = None
            if recorder is not None:
                await recorder.close()
