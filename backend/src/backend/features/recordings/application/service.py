from uuid import UUID

from backend.features.browsers.application.service import BrowserService
from backend.features.recordings.application.models import Recording
from backend.features.recordings.application.ports import Recorder


class RecordingService:
    """Own recording orchestration while the worker only records video."""

    def __init__(self, browsers: BrowserService, recorder: Recorder) -> None:
        self._browsers = browsers
        self._recorder = recorder

    async def start(self, browser_id: UUID) -> Recording:
        browser = await self._browsers.get(browser_id)
        return await self._recorder.start(browser)

    async def inspect(self, browser_id: UUID, recording_id: UUID) -> Recording:
        browser = await self._browsers.get(browser_id)
        return await self._recorder.inspect(browser, recording_id)

    async def stop(self, browser_id: UUID, recording_id: UUID) -> Recording:
        browser = await self._browsers.get(browser_id)
        return await self._recorder.stop_and_store(browser, recording_id)
