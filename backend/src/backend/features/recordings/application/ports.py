from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.browsers.domain.models import Browser
from backend.features.recordings.application.models import Recording


class Recorder(ABC):
    """Control recordings and persist their completed video."""

    @abstractmethod
    async def start(self, browser: Browser) -> Recording: ...

    @abstractmethod
    async def inspect(self, browser: Browser, recording_id: UUID) -> Recording: ...

    @abstractmethod
    async def stop_and_store(
        self, browser: Browser, recording_id: UUID
    ) -> Recording: ...

    @abstractmethod
    async def file(self, browser: Browser, recording_id: UUID) -> bytes: ...
