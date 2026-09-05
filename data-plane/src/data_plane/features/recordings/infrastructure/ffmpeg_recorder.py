import asyncio
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, suppress
from pathlib import Path

from data_plane.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from data_plane.features.recordings.application.models import (
    RecordedVideo,
    RecordingFormat,
)
from data_plane.features.recordings.application.ports import ScreenRecorder
from data_plane.features.recordings.infrastructure.ffmpeg import VideoRecorder
from data_plane.features.screencast.application.ports import FrameStream
from data_plane.features.screencast.infrastructure.tasks import cancel_and_wait
from data_plane.settings import DataPlaneSettings


class FfmpegScreenRecorder(ScreenRecorder):
    """Record raw active-tab screencast frames through FFmpeg."""

    def __init__(self, stream: FrameStream, settings: DataPlaneSettings) -> None:
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
                anext(frames), self._settings.recording_start_timeout
            )
            path = directory / "0.mp4"
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
