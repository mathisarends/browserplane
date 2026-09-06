import asyncio
import logging
import shutil
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, suppress
from pathlib import Path

import imageio_ffmpeg

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.application.models import (
    RecordedVideo,
    RecordingFormat,
)
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings
from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.shared.tasks import cancel_and_wait

logger = logging.getLogger(__name__)


class FfmpegScreenRecorder(ScreenRecorder):
    """Record raw active-tab screencast frames through FFmpeg."""

    def __init__(self, stream: FrameStream, settings: RecordingSettings) -> None:
        self._stream = stream
        self._settings = settings
        self._scope: AsyncExitStack | None = None
        self._writer: asyncio.Task[None] | None = None
        self._video: VideoRecorder | None = None
        self._path: Path | None = None
        self._failure: Exception | None = None

    async def start(self, directory: Path) -> None:
        scope = AsyncExitStack()
        frames = await scope.enter_async_context(self._stream.subscribe())
        try:
            first_frame = await asyncio.wait_for(
                anext(frames), self._settings.start_timeout
            )
            path = directory / "video.mp4"
            video = VideoRecorder(path)
            await video.start()
            await video.write(first_frame)
        except BaseException as error:
            with suppress(Exception):
                await scope.aclose()
            if isinstance(error, asyncio.CancelledError):
                raise
            message = (
                "Browser produced no screencast frames"
                if isinstance(error, TimeoutError | StopAsyncIteration)
                else str(error)
            )
            raise RecordingFailedException(message) from error

        self._scope = scope
        self._video = video
        self._path = path
        self._writer = asyncio.create_task(
            self._write_frames(frames), name="recording:frames"
        )

    async def stop(self) -> RecordedVideo:
        await self._stop_writer()
        await self._leave_stream()
        video, self._video = self._video, None
        if video is not None:
            await video.stop()
        if self._failure is not None:
            raise RecordingFailedException(str(self._failure)) from self._failure
        if self._path is None:
            raise RecordingFailedException("Recording was not started")
        size = self._path.stat().st_size if self._path.exists() else 0
        if size == 0:
            raise RecordingFailedException("FFmpeg returned an empty recording")
        return RecordedVideo(
            path=self._path,
            size_bytes=size,
            format=RecordingFormat.MP4,
        )

    async def close(self) -> None:
        await self._stop_writer()
        await self._leave_stream()
        video, self._video = self._video, None
        if video is not None:
            with suppress(Exception):
                await video.stop()

    async def _write_frames(self, frames: AsyncIterator[bytes]) -> None:
        try:
            async for frame in frames:
                assert self._video is not None
                await self._video.write(frame)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._failure = error

    async def _stop_writer(self) -> None:
        writer, self._writer = self._writer, None
        if writer is not None:
            await cancel_and_wait(writer)

    async def _leave_stream(self) -> None:
        scope, self._scope = self._scope, None
        if scope is not None:
            with suppress(Exception):
                await scope.aclose()


class VideoRecorder:
    """Encode a stream of JPEG frames into one MP4 file."""

    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._process: asyncio.subprocess.Process | None = None
        self._recording = False
        self._pipe_broken = False
        self._write_lock = asyncio.Lock()

    async def start(self) -> None:
        if self._recording:
            return
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.unlink(missing_ok=True)
        self._process = await Ffmpeg().run(_recording_command(self._output_path))
        self._pipe_broken = False
        self._recording = True
        logger.info("Video recorder started -> %s", self._output_path)

    async def write(self, frame: bytes) -> None:
        if not self._recording:
            return
        process = self._process
        if self._pipe_broken or process is None or process.stdin is None:
            raise RuntimeError("FFmpeg input pipe is unavailable")
        async with self._write_lock:
            try:
                process.stdin.write(frame)
                await process.stdin.drain()
            except (BrokenPipeError, ConnectionResetError) as error:
                self._pipe_broken = True
                self._recording = False
                raise RuntimeError("FFmpeg input pipe broke") from error

    async def stop(self) -> None:
        process, self._process = self._process, None
        self._recording = False
        if process is None:
            return
        if process.stdin is not None and not process.stdin.is_closing():
            process.stdin.close()
        try:
            return_code = await asyncio.wait_for(process.wait(), timeout=10.0)
        except TimeoutError:
            logger.warning("FFmpeg did not exit in time; killing it")
            process.kill()
            return_code = await process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg exited with code {return_code}")
        logger.info("Video recorder stopped -> %s", self._output_path)


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


def _recording_command(output_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-use_wallclock_as_timestamps",
        "1",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "vfr",
        "-crf",
        "23",
        "-movflags",
        "+faststart",
        "-y",
        str(output_path),
    ]
