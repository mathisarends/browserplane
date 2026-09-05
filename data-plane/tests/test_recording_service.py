from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from data_plane.features.browsers.application.ports import BrowserProcess
from data_plane.features.browsers.application.service import BrowserService
from data_plane.features.recordings.application.models import (
    RecordedSegment,
    RecordingFormat,
    RecordingState,
)
from data_plane.features.recordings.application.ports import ScreenRecorder
from data_plane.features.recordings.application.service import RecordingService
from data_plane.infrastructure.bucket.port import NullBucket
from data_plane.settings import DataPlaneSettings


class FakeProcess(BrowserProcess):
    async def start(self) -> str:
        return "ws://chromium/devtools/browser/test"

    async def stop(self) -> None:
        return None


class FakeRecorder(ScreenRecorder):
    """Record two tabs, the way a tab switch splits a recording."""

    closed = False

    def __init__(self) -> None:
        self._directory: Path | None = None

    async def start(self, directory: Path) -> None:
        self._directory = directory

    async def stop(self) -> tuple[RecordedSegment, ...]:
        assert self._directory is not None
        now = datetime.now(UTC)
        segments = []
        for index, data in enumerate((b"tab-one", b"tab-two")):
            path = self._directory / str(index)
            path.write_bytes(data)
            segments.append(
                RecordedSegment(
                    index=index,
                    target_id=f"target-{index}",
                    path=path,
                    size_bytes=len(data),
                    format=RecordingFormat.MP4,
                    started_at=now,
                    stopped_at=now,
                )
            )
        return tuple(segments)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_service_records_the_active_tab_into_segments() -> None:
    settings = DataPlaneSettings(_env_file=None)
    browsers = BrowserService(settings, process_factory=lambda _: FakeProcess())
    recorder = FakeRecorder()
    service = RecordingService(browsers, settings, lambda *_: recorder, NullBucket())

    browser = await browsers.create(uuid4())
    recording = await service.start(browser.id)
    assert recording.state is RecordingState.RECORDING

    stopped = await service.stop(browser.id, recording.id)
    assert stopped.state is RecordingState.COMPLETED
    assert stopped.size_bytes == len(b"tab-one") + len(b"tab-two")

    video = service.segment_file(browser.id, recording.id, 1)
    assert video.media_type == "video/mp4"
    assert video.path.read_bytes() == b"tab-two"

    await service.destroy()
    assert recorder.closed is True
