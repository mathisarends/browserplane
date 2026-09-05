import subprocess
from pathlib import Path

import pytest
from tests.fakes import FakeFrameStream

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.infrastructure.ffmpeg import Ffmpeg
from browser_worker.features.recordings.infrastructure.ffmpeg_recorder import (
    FfmpegScreenRecorder,
)
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings


def recorder(frames: tuple[bytes, ...]) -> FfmpegScreenRecorder:
    return FfmpegScreenRecorder(
        FakeFrameStream(*frames),
        RecordingSettings(_env_file=None, start_timeout=1),
    )


def jpeg_frame(directory: Path) -> bytes:
    path = directory / "frame.jpg"
    subprocess.run(
        [
            Ffmpeg().path,
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=16x16",
            "-frames:v",
            "1",
            "-y",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return path.read_bytes()


@pytest.mark.asyncio
async def test_records_screencast_frames_to_mp4(tmp_path: Path) -> None:
    frame = jpeg_frame(tmp_path)
    screen_recorder = recorder((frame, frame))

    await screen_recorder.start(tmp_path)
    video = await screen_recorder.stop()

    assert video.path == tmp_path / "0.mp4"
    assert video.size_bytes == video.path.stat().st_size
    assert video.size_bytes > 0
    assert video.format.media_type == "video/mp4"


@pytest.mark.asyncio
async def test_rejects_a_stream_without_frames(tmp_path: Path) -> None:
    with pytest.raises(RecordingFailedException, match="no screencast frames"):
        await recorder(()).start(tmp_path)


@pytest.mark.asyncio
async def test_stop_before_start_is_rejected() -> None:
    with pytest.raises(RecordingFailedException, match="was not started"):
        await recorder(()).stop()
