import asyncio
import base64
import logging
from contextlib import suppress
from dataclasses import dataclass

from cdpify import CDPSession, Client
from cdpify.domains.page.events import (
    PageEvent,
    ScreencastFrameEvent,
    ScreencastVisibilityChangedEvent,
)
from cdpify.domains.target.events import (
    DetachedFromTargetEvent,
    TargetCrashedEvent,
    TargetCreatedEvent,
    TargetDestroyedEvent,
    TargetEvent,
)
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _Frame:
    target_id: str
    data: bytes


@dataclass(frozen=True, slots=True)
class _VisibilityChanged:
    target_id: str
    visible: bool


@dataclass(frozen=True, slots=True)
class _TargetAdded:
    target_id: str


@dataclass(frozen=True, slots=True)
class _TargetRemoved:
    target_id: str


@dataclass(frozen=True, slots=True)
class _TargetDetached:
    target_id: str


type _StreamEvent = (
    _Frame | _VisibilityChanged | _TargetAdded | _TargetRemoved | _TargetDetached
)


class _VisibleTarget:
    def __init__(self) -> None:
        self._target_id: str | None = None
        self._hidden: set[str] = set()

    def remove(self, target_id: str) -> None:
        self._hidden.discard(target_id)
        if self._target_id == target_id:
            self._target_id = None

    def change_visibility(self, target_id: str, *, visible: bool) -> None:
        if visible:
            self._hidden.discard(target_id)
            self._target_id = target_id
        else:
            self._hidden.add(target_id)
            if self._target_id == target_id:
                self._target_id = None

    def frame(self, event: _Frame) -> bytes | None:
        if event.target_id in self._hidden:
            return None
        if self._target_id is None:
            self._target_id = event.target_id
        return event.data if self._target_id == event.target_id else None


async def stream_screencast(
    websocket: WebSocket,
    cdp_url: str,
    *,
    quality: int,
    width: int,
    height: int,
) -> None:
    """Follow the visible tab and send its latest JPEG frame as binary data."""
    await websocket.accept()
    try:
        async with Client(cdp_url) as client:
            await _stream_pages(
                websocket,
                client,
                quality=quality,
                width=width,
                height=height,
            )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Screencast websocket stopped unexpectedly")
        if websocket.application_state is not WebSocketState.DISCONNECTED:
            with suppress(Exception):
                await websocket.close(
                    code=1011, reason="Browser screencast unavailable"
                )


async def _stream_pages(
    websocket: WebSocket,
    client: Client,
    *,
    quality: int,
    width: int,
    height: int,
) -> None:
    events: asyncio.Queue[_StreamEvent] = asyncio.Queue()
    frames: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
    page_tasks: dict[str, asyncio.Task[None]] = {}
    target_tasks = (
        asyncio.create_task(_listen_target_created(client, events)),
        asyncio.create_task(_listen_target_destroyed(client, events)),
        asyncio.create_task(_listen_target_crashed(client, events)),
        asyncio.create_task(_listen_target_detached(client, events)),
    )
    sender = asyncio.create_task(_send_frames(websocket, frames))
    disconnected = asyncio.create_task(_wait_for_disconnect(websocket))
    next_event = asyncio.create_task(events.get())
    visible_target = _VisibleTarget()
    try:
        await asyncio.sleep(0)
        await client.target.set_discover_targets(discover=True)
        targets = await client.target.get_targets()
        for target in targets.target_infos:
            if target.type == "page":
                _start_page(
                    page_tasks,
                    target.target_id,
                    client,
                    events,
                    quality=quality,
                    width=width,
                    height=height,
                )

        while True:
            done, _ = await asyncio.wait(
                (next_event, sender, disconnected),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if disconnected in done:
                return
            if sender in done:
                await sender
                return

            event = next_event.result()
            next_event = asyncio.create_task(events.get())
            if isinstance(event, _TargetAdded):
                _start_page(
                    page_tasks,
                    event.target_id,
                    client,
                    events,
                    quality=quality,
                    width=width,
                    height=height,
                )
            elif isinstance(event, _TargetRemoved):
                task = page_tasks.pop(event.target_id, None)
                if task is not None:
                    await _cancel_tasks(task)
                visible_target.remove(event.target_id)
            elif isinstance(event, _TargetDetached):
                task = page_tasks.pop(event.target_id, None)
                if task is not None:
                    await _cancel_tasks(task)
                visible_target.remove(event.target_id)
                targets = await client.target.get_targets()
                if any(
                    target.type == "page" and target.target_id == event.target_id
                    for target in targets.target_infos
                ):
                    _start_page(
                        page_tasks,
                        event.target_id,
                        client,
                        events,
                        quality=quality,
                        width=width,
                        height=height,
                    )
            elif isinstance(event, _VisibilityChanged):
                visible_target.change_visibility(
                    event.target_id,
                    visible=event.visible,
                )
            elif (frame := visible_target.frame(event)) is not None:
                _publish_latest(frames, frame)
    finally:
        await _cancel_tasks(
            *target_tasks,
            *page_tasks.values(),
            sender,
            disconnected,
            next_event,
        )


def _start_page(
    page_tasks: dict[str, asyncio.Task[None]],
    target_id: str,
    client: Client,
    events: asyncio.Queue[_StreamEvent],
    *,
    quality: int,
    width: int,
    height: int,
) -> None:
    if target_id in page_tasks:
        return
    page_tasks[target_id] = asyncio.create_task(
        _capture_page(
            client,
            target_id,
            events,
            quality=quality,
            width=width,
            height=height,
        ),
        name=f"screencast:{target_id}",
    )


async def _capture_page(
    client: Client,
    target_id: str,
    events: asyncio.Queue[_StreamEvent],
    *,
    quality: int,
    width: int,
    height: int,
) -> None:
    session: CDPSession | None = None
    listeners: tuple[asyncio.Task[None], ...] = ()
    try:
        attached = await client.target.attach_to_target(
            target_id=target_id,
            flatten=True,
        )
        session = client.session(attached.session_id)
        await session.page.enable()
        listeners = (
            asyncio.create_task(_listen_frames(session, target_id, events)),
            asyncio.create_task(_listen_visibility(session, target_id, events)),
        )
        await asyncio.sleep(0)
        await session.page.start_screencast(
            format="jpeg",
            quality=quality,
            max_width=width,
            max_height=height,
        )
        await asyncio.gather(*listeners)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.debug("Page screencast ended for target %s", target_id, exc_info=True)
    finally:
        await _cancel_tasks(*listeners)
        if session is not None:
            with suppress(Exception):
                await session.page.stop_screencast()
            with suppress(Exception):
                await client.target.detach_from_target(session_id=session.session_id)


async def _listen_frames(
    session: CDPSession,
    target_id: str,
    events: asyncio.Queue[_StreamEvent],
) -> None:
    async for event in session.listen(PageEvent.SCREENCAST_FRAME, ScreencastFrameEvent):
        try:
            await events.put(_Frame(target_id, base64.b64decode(event.data)))
        finally:
            await session.page.screencast_frame_ack(session_id=event.session_id)


async def _listen_visibility(
    session: CDPSession,
    target_id: str,
    events: asyncio.Queue[_StreamEvent],
) -> None:
    async for event in session.listen(
        PageEvent.SCREENCAST_VISIBILITY_CHANGED,
        ScreencastVisibilityChangedEvent,
    ):
        await events.put(_VisibilityChanged(target_id, event.visible))


async def _listen_target_created(
    client: Client,
    events: asyncio.Queue[_StreamEvent],
) -> None:
    async for event in client.listen(
        TargetEvent.TARGET_CREATED,
        TargetCreatedEvent,
    ):
        if event.target_info.type == "page":
            await events.put(_TargetAdded(event.target_info.target_id))


async def _listen_target_destroyed(
    client: Client,
    events: asyncio.Queue[_StreamEvent],
) -> None:
    async for event in client.listen(
        TargetEvent.TARGET_DESTROYED,
        TargetDestroyedEvent,
    ):
        await events.put(_TargetRemoved(event.target_id))


async def _listen_target_crashed(
    client: Client,
    events: asyncio.Queue[_StreamEvent],
) -> None:
    async for event in client.listen(TargetEvent.TARGET_CRASHED, TargetCrashedEvent):
        await events.put(_TargetRemoved(event.target_id))


async def _listen_target_detached(
    client: Client,
    events: asyncio.Queue[_StreamEvent],
) -> None:
    async for event in client.listen(
        TargetEvent.DETACHED_FROM_TARGET,
        DetachedFromTargetEvent,
    ):
        if event.target_id is not None:
            await events.put(_TargetDetached(event.target_id))


async def _send_frames(websocket: WebSocket, frames: asyncio.Queue[bytes]) -> None:
    while True:
        await websocket.send_bytes(await frames.get())


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


def _publish_latest(frames: asyncio.Queue[bytes], frame: bytes) -> None:
    if frames.full():
        frames.get_nowait()
    frames.put_nowait(frame)


async def _cancel_tasks(*tasks: asyncio.Task[object]) -> None:
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
