import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.application.models import RecordingFormat
from browser_worker.features.recordings.infrastructure.cdp import (
    CdpScreenRecorder,
    TabRecorder,
)
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings

WEBM_HEADER = b"\x1a\x45\xdf\xa3webm-header"
MP4_HEADER = b"\x00\x00\x00\x18ftypisom"


class FakeTabRecorder(TabRecorder):
    """A browser that hands over a finished video in chunks."""

    def __init__(self, *chunks: bytes) -> None:
        self._chunks = chunks
        self.started = False
        self.closed = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> AsyncGenerator[bytes]:
        for chunk in self._chunks:
            yield chunk

    async def close(self) -> None:
        self.closed = True


class HangingTabRecorder(FakeTabRecorder):
    async def start(self) -> None:
        await asyncio.Event().wait()


def recorder(tab: TabRecorder) -> CdpScreenRecorder:
    return CdpScreenRecorder(tab, RecordingSettings(_env_file=None, start_timeout=0.01))


@pytest.mark.asyncio
async def test_saves_the_webm_the_browser_recorded(tmp_path: Path) -> None:
    tab = FakeTabRecorder(WEBM_HEADER, b"tab-one", b"tab-two")
    screen_recorder = recorder(tab)

    await screen_recorder.start(tmp_path)
    video = await screen_recorder.stop()

    assert tab.started is True
    assert video.path == tmp_path / "video.webm"
    assert video.format is RecordingFormat.WEBM
    assert video.path.read_bytes() == WEBM_HEADER + b"tab-one" + b"tab-two"
    assert video.size_bytes == video.path.stat().st_size


@pytest.mark.asyncio
async def test_saves_an_mp4_under_its_own_extension(tmp_path: Path) -> None:
    screen_recorder = recorder(FakeTabRecorder(MP4_HEADER, b"frames"))

    await screen_recorder.start(tmp_path)
    video = await screen_recorder.stop()

    assert video.path == tmp_path / "video.mp4"
    assert video.format is RecordingFormat.MP4
    assert video.format.media_type == "video/mp4"


@pytest.mark.asyncio
async def test_recognises_the_container_across_chunk_boundaries(
    tmp_path: Path,
) -> None:
    chunks = tuple(MP4_HEADER[index : index + 3] for index in range(0, 12, 3))
    screen_recorder = recorder(FakeTabRecorder(*chunks))

    await screen_recorder.start(tmp_path)
    video = await screen_recorder.stop()

    assert video.format is RecordingFormat.MP4
    assert video.path.read_bytes() == MP4_HEADER


@pytest.mark.asyncio
async def test_rejects_a_container_it_cannot_name(tmp_path: Path) -> None:
    screen_recorder = recorder(FakeTabRecorder(b"not-a-video-at-all"))
    await screen_recorder.start(tmp_path)

    with pytest.raises(RecordingFailedException, match="unknown video container"):
        await screen_recorder.stop()


@pytest.mark.asyncio
async def test_rejects_a_recording_without_video(tmp_path: Path) -> None:
    screen_recorder = recorder(FakeTabRecorder())
    await screen_recorder.start(tmp_path)

    with pytest.raises(RecordingFailedException, match="empty recording"):
        await screen_recorder.stop()


@pytest.mark.asyncio
async def test_stop_before_start_is_rejected() -> None:
    with pytest.raises(RecordingFailedException, match="was not started"):
        await recorder(FakeTabRecorder(WEBM_HEADER)).stop()


@pytest.mark.asyncio
async def test_a_browser_that_never_starts_releases_the_tab(tmp_path: Path) -> None:
    tab = HangingTabRecorder()
    screen_recorder = recorder(tab)

    with pytest.raises(RecordingFailedException, match="did not start recording"):
        await screen_recorder.start(tmp_path)

    assert tab.closed is True


@pytest.mark.asyncio
async def test_closing_releases_the_browser(tmp_path: Path) -> None:
    tab = FakeTabRecorder(WEBM_HEADER)
    screen_recorder = recorder(tab)
    await screen_recorder.start(tmp_path)

    await screen_recorder.close()

    assert tab.closed is True
    with pytest.raises(RecordingFailedException, match="was not started"):
        await screen_recorder.stop()
