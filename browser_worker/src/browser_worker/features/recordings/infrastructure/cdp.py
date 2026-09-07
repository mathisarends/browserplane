import asyncio
import base64
import logging
from collections.abc import AsyncGenerator
from contextlib import aclosing, suppress
from pathlib import Path
from typing import Protocol

from cdpify import CDPSession, Client

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.application.models import (
    RecordedVideo,
    RecordingFormat,
)
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings

logger = logging.getLogger(__name__)

READ_CHUNK_BYTES = 1 << 20
WEBM_SIGNATURE = b"\x1a\x45\xdf\xa3"
MP4_SIGNATURE = b"ftyp"
SIGNATURE_BYTES = 12


class TabRecorder(Protocol):
    """One browser tab that the browser itself records into a video file."""

    async def start(self) -> None:
        """Make the browser start recording the tab."""

    def stop(self) -> AsyncGenerator[bytes]:
        """Stop recording and yield the finished video in chunks."""

    async def close(self) -> None:
        """Release the browser resources held for this recording."""


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
            signature = await _read_signature(chunks)
            video_format = _container_format(signature)
            path = directory / f"video.{video_format.value}"
            size = await _write_video(path, signature, chunks)
        logger.info("Browser recording saved -> %s (%d bytes)", path, size)
        return RecordedVideo(path=path, size_bytes=size, format=video_format)


class CdpTabRecorder(TabRecorder):
    """Drive ``Page.startScreenRecording`` on one page of a browser."""

    def __init__(self, cdp_url: str, settings: RecordingSettings) -> None:
        self._cdp_url = cdp_url
        self._settings = settings
        self._client: Client | None = None
        self._session: CDPSession | None = None

    async def start(self) -> None:
        if self._session is not None:
            raise RecordingFailedException("This browser is already being recorded")
        client = Client(self._cdp_url)
        await client.connect()
        self._client = client
        try:
            session = await self._attach_to_page(client)
            await session.page.start_screen_recording(
                audio=self._settings.audio,
                frame_rate=self._settings.frame_rate,
            )
        except BaseException:
            await self._disconnect()
            raise
        self._session = session
        logger.info("Browser recording started on session %s", session.session_id)

    async def stop(self) -> AsyncGenerator[bytes]:
        session, self._session = self._session, None
        if session is None:
            raise RecordingFailedException("Recording was not started")
        try:
            recording = await session.page.stop_screen_recording()
            async for chunk in _read_stream(session, recording.stream):
                yield chunk
        finally:
            await self._disconnect()

    async def close(self) -> None:
        session, self._session = self._session, None
        if session is not None:
            with suppress(Exception):
                await session.page.stop_screen_recording()
        await self._disconnect()

    async def _attach_to_page(self, client: Client) -> CDPSession:
        targets = await client.target.get_targets()
        page = next(
            (target for target in targets.target_infos if target.type == "page"),
            None,
        )
        if page is None:
            raise RecordingFailedException("Browser has no page to record")
        attached = await client.target.attach_to_target(
            target_id=page.target_id,
            flatten=True,
        )
        return client.session(attached.session_id)

    async def _disconnect(self) -> None:
        client, self._client = self._client, None
        self._session = None
        if client is not None:
            with suppress(Exception):
                await client.disconnect()


async def _read_stream(session: CDPSession, handle: str) -> AsyncGenerator[bytes]:
    """Drain one CDP IO stream, decoding the chunks as the browser encoded them."""
    try:
        while True:
            chunk = await session.io.read(handle=handle, size=READ_CHUNK_BYTES)
            data = (
                base64.b64decode(chunk.data)
                if chunk.base64_encoded
                else chunk.data.encode()
            )
            if data:
                yield data
            if chunk.eof:
                return
    finally:
        with suppress(Exception):
            await session.io.close(handle=handle)


async def _read_signature(chunks: AsyncGenerator[bytes]) -> bytes:
    """Collect enough leading bytes to recognise the container."""
    signature = bytearray()
    async for chunk in chunks:
        signature += chunk
        if len(signature) >= SIGNATURE_BYTES:
            break
    if not signature:
        raise RecordingFailedException("Browser returned an empty recording")
    return bytes(signature)


def _container_format(signature: bytes) -> RecordingFormat:
    """Name the container the browser chose for this recording."""
    if signature.startswith(WEBM_SIGNATURE):
        return RecordingFormat.WEBM
    if signature[4:8] == MP4_SIGNATURE:
        return RecordingFormat.MP4
    raise RecordingFailedException("Browser returned an unknown video container")


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
