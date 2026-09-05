from abc import ABC, abstractmethod
from pathlib import Path

from data_plane.features.recordings.application.models import RecordedVideo


class ScreenRecorder(ABC):
    """Records the active tab of one browser, following it across tab switches."""

    @abstractmethod
    async def start(self, directory: Path) -> None:
        """Attach to the active-tab stream and write into ``directory``."""

    @abstractmethod
    async def stop(self) -> RecordedVideo:
        """Stop recording and return the completed video."""

    @abstractmethod
    async def close(self) -> None:
        """Release the browser resources this recorder holds."""
