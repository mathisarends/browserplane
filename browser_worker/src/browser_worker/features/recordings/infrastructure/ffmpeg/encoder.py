import asyncio
import logging
from pathlib import Path

from browser_worker.features.recordings.infrastructure.ffmpeg.binary import Ffmpeg

logger = logging.getLogger(__name__)

_STOP_TIMEOUT = 10.0


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
            return_code = await asyncio.wait_for(process.wait(), timeout=_STOP_TIMEOUT)
        except TimeoutError:
            logger.warning("FFmpeg did not exit in time; killing it")
            process.kill()
            return_code = await process.wait()
        if return_code != 0:
            raise RuntimeError(f"FFmpeg exited with code {return_code}")
        logger.info("Video recorder stopped -> %s", self._output_path)


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
