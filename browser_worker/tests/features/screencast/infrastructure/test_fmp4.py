import asyncio
import subprocess
from pathlib import Path

import pytest

from browser_worker.features.recordings.infrastructure.ffmpeg import Ffmpeg
from browser_worker.features.screencast.infrastructure.fmp4 import Fmp4Livestream


def jpeg_frame(directory: Path) -> bytes:
    path = directory / "frame.jpg"
    subprocess.run(
        [
            Ffmpeg().path,
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=16x16",
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
async def test_streams_an_initialization_segment_and_media_fragment(
    tmp_path: Path,
) -> None:
    livestream = Fmp4Livestream()
    await livestream.start()

    try:
        async with livestream.stream() as chunks:
            frame = jpeg_frame(tmp_path)

            async def publish_frames() -> None:
                for _ in range(60):
                    await livestream.publish_frame(frame)
                    await asyncio.sleep(0.04)

            publisher = asyncio.create_task(publish_frames())
            initialization = await asyncio.wait_for(anext(chunks), timeout=5)
            fragment = await asyncio.wait_for(anext(chunks), timeout=5)
            await publisher
    finally:
        await livestream.stop()

    assert b"ftyp" in initialization
    assert b"moov" in initialization
    assert b"moof" in fragment
    assert b"mdat" in fragment


@pytest.mark.asyncio
async def test_publish_and_stop_are_safe_before_start() -> None:
    livestream = Fmp4Livestream()

    await livestream.publish_frame(b"unused")
    await livestream.stop()
