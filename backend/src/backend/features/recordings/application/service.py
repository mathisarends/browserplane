from uuid import UUID

from backend.features.browsers.application.service import BrowserService
from backend.features.recordings.application.ports import RecordingGateway
from generated.browser_worker import RecordingResponse


class RecordingService:
    """Own recording orchestration while the worker only records video."""

    def __init__(self, browsers: BrowserService, recordings: RecordingGateway) -> None:
        self._browsers = browsers
        self._recordings = recordings

    async def start(self, browser_id: UUID) -> RecordingResponse:
        browser = await self._browsers.get(browser_id)
        return await self._recordings.start(browser)

    async def inspect(self, browser_id: UUID, recording_id: UUID) -> RecordingResponse:
        browser = await self._browsers.get(browser_id)
        return await self._recordings.inspect(browser, recording_id)

    async def stop(self, browser_id: UUID, recording_id: UUID) -> RecordingResponse:
        browser = await self._browsers.get(browser_id)
        return await self._recordings.stop_and_store(browser, recording_id)
