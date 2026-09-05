from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.browsers.application.models import Browser
from generated.browser_worker import RecordingResponse


class RecordingGateway(ABC):
    """Control recordings on a worker and transfer completed video to storage."""

    @abstractmethod
    async def start(self, browser: Browser) -> RecordingResponse: ...

    @abstractmethod
    async def inspect(
        self, browser: Browser, recording_id: UUID
    ) -> RecordingResponse: ...

    @abstractmethod
    async def stop_and_store(
        self, browser: Browser, recording_id: UUID
    ) -> RecordingResponse: ...
