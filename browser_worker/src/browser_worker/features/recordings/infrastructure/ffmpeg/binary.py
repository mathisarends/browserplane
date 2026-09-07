import asyncio
import logging
import shutil

import imageio_ffmpeg

logger = logging.getLogger(__name__)


class Ffmpeg:
    """Start FFmpeg from the system or the imageio-ffmpeg fallback."""

    def __init__(self) -> None:
        self.path = self._find_executable()
        logger.debug("Using FFmpeg at %s", self.path)

    @staticmethod
    def _find_executable() -> str:
        if system_ffmpeg := shutil.which("ffmpeg"):
            return system_ffmpeg
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as error:
            raise RuntimeError(
                "FFmpeg not found; install it system-wide or install imageio-ffmpeg"
            ) from error

    async def run(self, command: list[str]) -> asyncio.subprocess.Process:
        if not command:
            raise ValueError("FFmpeg command cannot be empty")
        prepared = [self.path, *command[1:]]
        logger.debug("Starting FFmpeg: %s", " ".join(prepared))
        process = await asyncio.create_subprocess_exec(
            *prepared,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(
            self._log_stderr(process.stderr),
            name="recording:ffmpeg-stderr",
        )
        return process

    @staticmethod
    async def _log_stderr(stream: asyncio.StreamReader | None) -> None:
        if stream is None:
            return
        async for line in stream:
            message = line.decode(errors="replace").strip()
            if message:
                logger.debug("[FFmpeg] %s", message)
