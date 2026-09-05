from pathlib import Path
from uuid import uuid4

import pytest
from tests.fakes import FakeBrowserProcess

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.recordings.application.models import (
    RecordedVideo,
    RecordingFormat,
    RecordingState,
)
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.workspace.application.workspace import Workspace


class FakeRecorder(ScreenRecorder):
    closed = False

    def __init__(self) -> None:
        self._directory: Path | None = None

    async def start(self, directory: Path) -> None:
        self._directory = directory

    async def stop(self) -> RecordedVideo:
        assert self._directory is not None
        data = b"tab-one-tab-two"
        path = self._directory / "0.mp4"
        path.write_bytes(data)
        return RecordedVideo(
            path=path,
            size_bytes=len(data),
            format=RecordingFormat.MP4,
        )

    async def close(self) -> None:
        self.closed = True


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

    video = service.file(browser.id, recording.id)
    assert video.media_type == "video/mp4"
    assert video.path.read_bytes() == b"tab-one-tab-two"

    await service.destroy()
    assert recorder.closed is True
