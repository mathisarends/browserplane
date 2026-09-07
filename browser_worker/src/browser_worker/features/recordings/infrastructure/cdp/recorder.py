import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import aclosing, suppress
from pathlib import Path

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.application.models import RecordedVideo
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.infrastructure.cdp.container import (
    container_format,
    read_signature,
)
from browser_worker.features.recordings.infrastructure.cdp.ports import TabRecorder
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings

logger = logging.getLogger(__name__)


class CdpScreenRecorder(ScreenRecorder):
    """Record with Chromium's own screen recorder instead of FFmpeg.

    The browser encodes the video and hands it over as one finished file when
    the recording stops, so no frames pass through this process while it runs.
    It records the tab it was started on: unlike the FFmpeg recorder it does not
    follow the user into another tab.
    """

    def __init__(self, tab: TabRecorder, settings: RecordingSettings) -> None:
        self._tab = tab
        self._settings = settings
        self._directory: Path | None = None

    async def start(self, directory: Path) -> None:
        try:
            await asyncio.wait_for(self._tab.start(), self._settings.start_timeout)
        except BaseException as error:
            with suppress(Exception):
                await self._tab.close()
            if isinstance(error, asyncio.CancelledError):
                raise
            message = (
                "Browser did not start recording in time"
                if isinstance(error, TimeoutError)
                else str(error)
            )
            raise RecordingFailedException(message) from error
        self._directory = directory

    async def stop(self) -> RecordedVideo:
        directory, self._directory = self._directory, None
        if directory is None:
            raise RecordingFailedException("Recording was not started")
        try:
            return await self._save_video(directory)
        except RecordingFailedException:
            raise
        except Exception as error:
            raise RecordingFailedException(str(error)) from error

    async def close(self) -> None:
        self._directory = None
        with suppress(Exception):
            await self._tab.close()

    async def _save_video(self, directory: Path) -> RecordedVideo:
        async with aclosing(self._tab.stop()) as chunks:
            signature = await read_signature(chunks)
            video_format = container_format(signature)
            path = directory / f"video.{video_format.value}"
            size = await _write_video(path, signature, chunks)
        logger.info("Browser recording saved -> %s (%d bytes)", path, size)
        return RecordedVideo(path=path, size_bytes=size, format=video_format)


async def _write_video(
    path: Path,
    signature: bytes,
    chunks: AsyncGenerator[bytes],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as video:
        written = video.write(signature)
        async for chunk in chunks:
            written += video.write(chunk)
    return written
