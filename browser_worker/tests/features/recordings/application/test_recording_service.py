from pathlib import Path
from uuid import uuid4

import pytest
from tests.fakes import FakeBrowserProcess

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.recordings.application.exceptions import (
    RecordingAlreadyExistsException,
    RecordingNotCompletedException,
    RecordingNotFoundException,
    RecordingNotRunningException,
)
from browser_worker.features.recordings.application.models import (
    RecordedVideo,
    RecordingFormat,
    RecordingState,
)
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.workspace.application.workspace import Workspace


class FakeRecorder(ScreenRecorder):
    def __init__(self) -> None:
        self._directory: Path | None = None
        self.closed = False

    async def start(self, directory: Path) -> None:
        self._directory = directory

    async def stop(self) -> RecordedVideo:
        assert self._directory is not None
        data = b"tab-one-tab-two"
        path = self._directory / "video.mp4"
        path.write_bytes(data)
        return RecordedVideo(
            path=path,
            size_bytes=len(data),
            format=RecordingFormat.MP4,
        )

    async def close(self) -> None:
        self.closed = True


class FailingRecorder(FakeRecorder):
    async def stop(self) -> RecordedVideo:
        raise RuntimeError("encoder stopped")


@pytest.mark.asyncio
async def test_service_records_the_active_tab_into_one_video(tmp_path: Path) -> None:
    browsers = BrowserService(FakeBrowserProcess())
    recorder = FakeRecorder()
    service = RecordingService(browsers, Workspace(tmp_path), lambda _: recorder)

    browser = await browsers.create(uuid4())
    recording = await service.start(browser.id)
    assert recording.state is RecordingState.RECORDING

    stopped = await service.stop(browser.id, recording.id)
    assert stopped.state is RecordingState.COMPLETED
    assert stopped.size_bytes == len(b"tab-one-tab-two")
    assert service.get(browser.id, recording.id) == stopped

    video = service.file(browser.id, recording.id)
    assert video.media_type == "video/mp4"
    assert video.path.read_bytes() == b"tab-one-tab-two"

    with pytest.raises(RecordingNotRunningException):
        await service.stop(browser.id, recording.id)
    with pytest.raises(RecordingAlreadyExistsException):
        await service.start(browser.id)

    await service.release()


@pytest.mark.asyncio
async def test_only_one_recording_can_run_at_a_time(tmp_path: Path) -> None:
    browsers = BrowserService(FakeBrowserProcess())
    recorder = FakeRecorder()
    service = RecordingService(browsers, Workspace(tmp_path), lambda _: recorder)
    browser = await browsers.create(uuid4())
    await service.start(browser.id)

    with pytest.raises(RecordingAlreadyExistsException):
        await service.start(browser.id)

    await service.release()
    assert recorder.closed is True


@pytest.mark.asyncio
async def test_unfinished_and_unknown_recordings_have_no_files(tmp_path: Path) -> None:
    browsers = BrowserService(FakeBrowserProcess())
    service = RecordingService(browsers, Workspace(tmp_path), lambda _: FakeRecorder())
    browser = await browsers.create(uuid4())
    recording = await service.start(browser.id)

    with pytest.raises(RecordingNotCompletedException):
        service.file(browser.id, recording.id)
    with pytest.raises(RecordingNotFoundException):
        service.get(browser.id, uuid4())

    await service.release()


@pytest.mark.asyncio
async def test_failed_stop_releases_the_browser_for_another_recording(
    tmp_path: Path,
) -> None:
    browsers = BrowserService(FakeBrowserProcess())
    failing_recorder = FailingRecorder()
    recorders = iter((failing_recorder, FakeRecorder()))
    service = RecordingService(browsers, Workspace(tmp_path), lambda _: next(recorders))
    browser = await browsers.create(uuid4())
    failed = await service.start(browser.id)

    with pytest.raises(RuntimeError, match="encoder stopped"):
        await service.stop(browser.id, failed.id)

    assert service.get(browser.id, failed.id).state is RecordingState.FAILED
    assert failing_recorder.closed is True
    replacement = await service.start(browser.id)
    assert replacement.state is RecordingState.RECORDING

    await service.release()
