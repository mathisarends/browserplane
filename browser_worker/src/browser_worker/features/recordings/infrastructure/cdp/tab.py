import base64
import logging
from collections.abc import AsyncGenerator
from contextlib import suppress

from cdpify import CDPSession, Client

from browser_worker.features.recordings.application.exceptions import (
    RecordingFailedException,
)
from browser_worker.features.recordings.infrastructure.cdp.ports import TabRecorder
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings

logger = logging.getLogger(__name__)

_READ_CHUNK_BYTES = 1 << 20


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
            chunk = await session.io.read(handle=handle, size=_READ_CHUNK_BYTES)
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
