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
    RecordedVideo,
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

    async def start(self, browser_id: UUID) -> Recording:
        async with self._lock:
            upstream_cdp_url = self._browsers.upstream_cdp_url(browser_id)
            if (
                self._recording is not None
                and self._recording.state is not RecordingState.FAILED
            ):
                raise RecordingAlreadyExistsException
            recording = Recording(
                id=uuid4(),
                browser_id=browser_id,
                state=RecordingState.RECORDING,
                started_at=datetime.now(UTC),
            )
            directory = self._workspace.create_recording_directory(recording.id)
            recorder = self._recorder_factory(upstream_cdp_url)
            await recorder.start(directory)
            self._recording = recording
            self._recorder = recorder
            return recording

    async def stop(self, browser_id: UUID, recording_id: UUID) -> Recording:
        async with self._lock:
            recording = self._get(browser_id, recording_id)
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

    def get(self, browser_id: UUID, recording_id: UUID) -> Recording:
        return self._get(browser_id, recording_id)

    def file(self, browser_id: UUID, recording_id: UUID) -> RecordingFile:
        return _to_file(recording_id, self._completed_video(browser_id, recording_id))

    async def release(self) -> None:
        """Close the active recorder and forget the in-memory history.

        The worker-level release owns deletion of files through ``Workspace.clear``.
        """
        async with self._lock:
            recorder, self._recorder = self._recorder, None
            self._recording = None
            if recorder is not None:
                await recorder.close()

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
        recording = self._recording
        if (
            recording is None
            or recording.id != recording_id
            or recording.browser_id != browser_id
        ):
            raise RecordingNotFoundException
        return recording


def _to_file(recording_id: UUID, video: RecordedVideo) -> RecordingFile:
    return RecordingFile(
        path=video.path,
        media_type=video.format.media_type,
        filename=f"{recording_id}.{video.format.value}",
    )
