from collections.abc import AsyncGenerator
from typing import Protocol


class TabRecorder(Protocol):
    """One browser tab that the browser itself records into a video file."""

    async def start(self) -> None:
        """Make the browser start recording the tab."""

    def stop(self) -> AsyncGenerator[bytes]:
        """Stop recording and yield the finished video in chunks."""

    async def close(self) -> None:
        """Release the browser resources held for this recording."""
