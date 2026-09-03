import asyncio
import base64
import logging
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cdpify import CDPSession, Client
from cdpify.domains.io import StreamHandle

from data_plane.features.browsers.infrastructure.screencast import (
    ActiveTabChanged,
    ActiveTabStream,
    PageUpdate,
    Subscription,
    cancel_and_wait,
)
from data_plane.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from data_plane.features.recordings.application.models import (
    RecordedSegment,
    RecordingFormat,
)
from data_plane.features.recordings.application.ports import ScreenRecorder
from data_plane.settings import DataPlaneSettings

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"
MP4_MAGIC = b"ftyp"


@dataclass(slots=True)
class OpenSegment:
    """The tab currently being recorded."""

    index: int
    target_id: str
    session: CDPSession
    started_at: datetime


class ChromeScreenRecorder(ScreenRecorder):
    """Record the active tab through ``Page.startScreenRecording``.

    The command is bound to one page target, so whenever Chromium shows a
    different tab the running recording is drained into a segment and a new one
    starts on the tab that took over.
    """

    def __init__(self, stream: ActiveTabStream, settings: DataPlaneSettings) -> None:
        self._stream = stream
        self._settings = settings
        self._subscription: AsyncExitStack | None = None
        self._follow: asyncio.Task[None] | None = None
        self._directory: Path | None = None
        self._open: OpenSegment | None = None
        self._segments: list[RecordedSegment] = []
        self._lock = asyncio.Lock()

    async def start(self, directory: Path) -> None:
        self._directory = directory
        subscription_scope = AsyncExitStack()
        subscription = await subscription_scope.enter_async_context(
            self._stream.subscribe()
        )
        try:
            target_id = await asyncio.wait_for(
                _first_active_tab(subscription.updates),
                self._settings.recording_start_timeout,
            )
            await self._open_segment(subscription.client, target_id)
        except BaseException as error:
            with suppress(Exception):
                await subscription_scope.aclose()
            raise _as_recording_failure(error) from error
        self._subscription = subscription_scope
        self._follow = asyncio.create_task(
            self._follow_active_tab(subscription),
            name="recording:follow",
        )

    async def stop(self) -> tuple[RecordedSegment, ...]:
        # The last segment is drained over the shared connection, so the stream
        # is only left once its video has been written.
        await self._stop_switching()
        async with self._lock:
            await self._close_segment()
        await self.close()
        if not self._segments:
            raise RecordingFailedException("Chromium returned no recorded video")
        return tuple(self._segments)

    async def close(self) -> None:
        await self._stop_switching()
        open_segment, self._open = self._open, None
        if open_segment is not None:
            with suppress(Exception):
                await open_segment.session.page.stop_screen_recording()
        await self._leave_stream()

    async def _stop_switching(self) -> None:
        """Stop following tab changes, leaving the current recording running."""
        follow, self._follow = self._follow, None
        if follow is not None:
            await cancel_and_wait(follow)

    async def _leave_stream(self) -> None:
        """Drop this recorder's share of the browser's active-tab stream."""
        subscription_scope, self._subscription = self._subscription, None
        if subscription_scope is not None:
            with suppress(Exception):
                await subscription_scope.aclose()

    async def _follow_active_tab(self, subscription: Subscription) -> None:
        try:
            async for update in subscription.updates:
                if isinstance(update, ActiveTabChanged):
                    await self._switch_to(subscription.client, update.target_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "Stopped following the active tab; recording stays on the current tab"
            )

    async def _switch_to(self, client: Client, target_id: str) -> None:
        async with self._lock:
            if self._open is None or self._open.target_id == target_id:
                return
            await self._close_segment()
            await self._open_segment(client, target_id)

    async def _open_segment(self, client: Client, target_id: str) -> None:
        attached = await client.target.attach_to_target(
            target_id=target_id,
            flatten=True,
        )
        session = client.session(attached.session_id)
        await session.page.start_screen_recording(
            audio=self._settings.recording_audio,
            max_width=self._settings.width,
            max_height=self._settings.height,
            frame_rate=self._settings.recording_frame_rate,
        )
        self._open = OpenSegment(
            index=len(self._segments),
            target_id=target_id,
            session=session,
            started_at=datetime.now(UTC),
        )

    async def _close_segment(self) -> None:
        """Drain the running recording; a tab that died takes its segment along."""
        open_segment, self._open = self._open, None
        if open_segment is None or self._directory is None:
            return
        path = self._directory / str(open_segment.index)
        try:
            stopped = await open_segment.session.page.stop_screen_recording()
            size = await _write_video(open_segment.session, stopped.stream, path)
        except Exception:
            logger.warning(
                "Dropped recording segment %s of target %s",
                open_segment.index,
                open_segment.target_id,
                exc_info=True,
            )
            path.unlink(missing_ok=True)
            return
        self._segments.append(
            RecordedSegment(
                index=open_segment.index,
                target_id=open_segment.target_id,
                path=path,
                size_bytes=size,
                format=_detect_format(path),
                started_at=open_segment.started_at,
                stopped_at=datetime.now(UTC),
            )
        )


async def _first_active_tab(updates: AsyncGenerator[PageUpdate]) -> str:
    async for update in updates:
        if isinstance(update, ActiveTabChanged):
            return update.target_id
    raise RecordingFailedException("Browser has no visible tab")


async def _write_video(
    session: CDPSession,
    handle: StreamHandle,
    destination: Path,
) -> int:
    size = 0
    try:
        with destination.open("wb") as video:
            while True:
                chunk = await session.io.read(handle=handle, size=CHUNK_SIZE)
                data = _decode(chunk.data, base64_encoded=chunk.base64_encoded)
                video.write(data)
                size += len(data)
                if chunk.eof:
                    break
    finally:
        with suppress(Exception):
            await session.io.close(handle=handle)
    if size == 0:
        raise RecordingFailedException("Chromium returned an empty recording")
    return size


def _decode(data: str, *, base64_encoded: bool | None) -> bytes:
    return base64.b64decode(data) if base64_encoded else data.encode("utf-8")


def _detect_format(path: Path) -> RecordingFormat:
    """Infer the container from the file header; CDP does not report it."""
    with path.open("rb") as video:
        header = video.read(12)
    if header.startswith(WEBM_MAGIC):
        return RecordingFormat.WEBM
    if header[4:8] == MP4_MAGIC:
        return RecordingFormat.MP4
    logger.warning("Unrecognised recording container, assuming WebM")
    return RecordingFormat.WEBM


def _as_recording_failure(error: BaseException) -> BaseException:
    if isinstance(error, TimeoutError):
        return RecordingFailedException("Browser has no visible tab")
    if isinstance(error, RecordingFailedException | asyncio.CancelledError):
        return error
    return RecordingFailedException(str(error))
