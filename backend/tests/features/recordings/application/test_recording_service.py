from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from backend.features.browsers.domain.models import Browser, BrowserSlot
from backend.features.recordings.application.models import Recording, RecordingState
from backend.features.recordings.application.ports import Recorder
from backend.features.recordings.application.service import RecordingService


class FakeBrowsers:
    def __init__(self, browser: Browser) -> None:
        self.browser = browser
        self.requested: list[UUID] = []

    async def get(self, browser_id: UUID) -> Browser:
        self.requested.append(browser_id)
        assert browser_id == self.browser.id
        return self.browser


class FakeRecorder(Recorder):
    def __init__(self, recording: Recording) -> None:
        self.recording = recording
        self.operations: list[str] = []

    async def start(self, browser: Browser) -> Recording:
        self.operations.append("start")
        return self.recording

    async def inspect(self, browser: Browser, recording_id: UUID) -> Recording:
        self.operations.append("inspect")
        assert recording_id == self.recording.id
        return self.recording

    async def stop_and_store(self, browser: Browser, recording_id: UUID) -> Recording:
        self.operations.append("stop")
        assert recording_id == self.recording.id
        return self.recording

    async def file(self, browser: Browser, recording_id: UUID) -> bytes:
        self.operations.append("file")
        assert recording_id == self.recording.id
        return b"video"


@pytest.mark.asyncio
async def test_recording_service_routes_each_operation_to_the_resolved_browser(
) -> None:
    browser = Browser(BrowserSlot(uuid4(), "http://worker"), datetime.now(UTC))
    recording = Recording(
        id=uuid4(),
        browser_id=browser.id,
        state=RecordingState.RECORDING,
        started_at=datetime.now(UTC),
        stopped_at=None,
        size_bytes=None,
    )
    browsers = FakeBrowsers(browser)
    recorder = FakeRecorder(recording)
    service = RecordingService(browsers, recorder)  # type: ignore[arg-type]

    assert await service.start(browser.id) == recording
    assert await service.inspect(browser.id, recording.id) == recording
    assert await service.stop(browser.id, recording.id) == recording
    assert await service.file(browser.id, recording.id) == b"video"
    assert browsers.requested == [browser.id] * 4
    assert recorder.operations == ["start", "inspect", "stop", "file"]
