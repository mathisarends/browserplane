from abc import ABC, abstractmethod
from pathlib import Path

from data_plane.features.recordings.application.models import RecordedSegment


class ScreenRecorder(ABC):
    """Records the active tab of one browser, following it across tab switches."""

    @abstractmethod
    async def start(self, directory: Path) -> None:
        """Attach to the active tab and record segments into ``directory``."""

    @abstractmethod
    async def stop(self) -> tuple[RecordedSegment, ...]:
        """Stop recording and return the segments written so far."""

    @abstractmethod
    async def close(self) -> None:
        """Release the browser resources this recorder holds."""
