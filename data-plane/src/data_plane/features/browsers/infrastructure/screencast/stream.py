import asyncio
import base64
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import suppress

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

from data_plane.features.browsers.infrastructure.screencast.models import (
    Frame,
    StreamEvent,
    TargetAdded,
    TargetDetached,
    TargetRemoved,
    VisibilityChanged,
    VisibleTarget,
)

logger = logging.getLogger(__name__)


class Screencast:
    """Publish the visible Chromium tab as a latest-frame JPEG stream."""

    def __init__(
        self,
        cdp_url: str,
        *,
        quality: int,
        width: int,
        height: int,
    ) -> None:
        self._client = Client(cdp_url)
        self._quality = quality
        self._width = width
        self._height = height

    def __aiter__(self) -> AsyncIterator[bytes]:
        return self.frames()

    async def frames(self) -> AsyncGenerator[bytes]:
        """Yield JPEG bytes, dropping stale frames when the consumer is slow."""
        frames: asyncio.Queue[bytes] = asyncio.Queue(maxsize=1)
        async with self._client:
            publisher = asyncio.create_task(
                self._publish_frames(frames),
                name="screencast:publisher",
            )
            next_frame = asyncio.create_task(frames.get())
            try:
                while True:
                    done, _ = await asyncio.wait(
                        (publisher, next_frame),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if publisher in done:
                        await _cancel_tasks(next_frame)
                        await publisher
                        raise RuntimeError("Screencast publisher stopped")
                    yield next_frame.result()
                    next_frame = asyncio.create_task(frames.get())
            finally:
                await _cancel_tasks(publisher, next_frame)

    async def _publish_frames(self, frames: asyncio.Queue[bytes]) -> None:
        events: asyncio.Queue[StreamEvent] = asyncio.Queue()
        page_tasks: dict[str, asyncio.Task[None]] = {}
        target_tasks = (
            asyncio.create_task(self._listen_target_created(events)),
            asyncio.create_task(self._listen_target_destroyed(events)),
            asyncio.create_task(self._listen_target_crashed(events)),
            asyncio.create_task(self._listen_target_detached(events)),
        )
        visible_target = VisibleTarget()
        try:
            await asyncio.sleep(0)
            await self._client.target.set_discover_targets(discover=True)
            targets = await self._client.target.get_targets()
            for target in targets.target_infos:
                if target.type == "page":
                    self._start_page(page_tasks, target.target_id, events)

            while True:
                event = await events.get()
                if isinstance(event, TargetAdded):
                    self._start_page(page_tasks, event.target_id, events)
                elif isinstance(event, TargetRemoved):
                    task = page_tasks.pop(event.target_id, None)
                    if task is not None:
                        await _cancel_tasks(task)
                    visible_target.remove(event.target_id)
                elif isinstance(event, TargetDetached):
                    task = page_tasks.pop(event.target_id, None)
                    if task is not None:
                        await _cancel_tasks(task)
                    visible_target.remove(event.target_id)
                    targets = await self._client.target.get_targets()
                    if any(
                        target.type == "page" and target.target_id == event.target_id
                        for target in targets.target_infos
                    ):
                        self._start_page(page_tasks, event.target_id, events)
                elif isinstance(event, VisibilityChanged):
                    visible_target.change_visibility(
                        event.target_id,
                        visible=event.visible,
                    )
                elif (frame := visible_target.frame(event)) is not None:
                    _publish_latest(frames, frame)
        finally:
            await _cancel_tasks(*target_tasks, *page_tasks.values())

    def _start_page(
        self,
        page_tasks: dict[str, asyncio.Task[None]],
        target_id: str,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        if target_id in page_tasks:
            return
        page_tasks[target_id] = asyncio.create_task(
            self._capture_page(target_id, events),
            name=f"screencast:{target_id}",
        )

    async def _capture_page(
        self,
        target_id: str,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        session: CDPSession | None = None
        listeners: tuple[asyncio.Task[None], ...] = ()
        try:
            attached = await self._client.target.attach_to_target(
                target_id=target_id,
                flatten=True,
            )
            session = self._client.session(attached.session_id)
            await session.page.enable()
            listeners = (
                asyncio.create_task(self._listen_frames(session, target_id, events)),
                asyncio.create_task(
                    self._listen_visibility(session, target_id, events)
                ),
            )
            await asyncio.sleep(0)
            await session.page.start_screencast(
                format="jpeg",
                quality=self._quality,
                max_width=self._width,
                max_height=self._height,
            )
            await asyncio.gather(*listeners)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug(
                "Page screencast ended for target %s",
                target_id,
                exc_info=True,
            )
        finally:
            await _cancel_tasks(*listeners)
            if session is not None:
                with suppress(Exception):
                    await session.page.stop_screencast()
                with suppress(Exception):
                    await self._client.target.detach_from_target(
                        session_id=session.session_id
                    )

    async def _listen_frames(
        self,
        session: CDPSession,
        target_id: str,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        async for event in session.listen(
            PageEvent.SCREENCAST_FRAME,
            ScreencastFrameEvent,
        ):
            try:
                await events.put(Frame(target_id, base64.b64decode(event.data)))
            finally:
                await session.page.screencast_frame_ack(session_id=event.session_id)

    async def _listen_visibility(
        self,
        session: CDPSession,
        target_id: str,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        async for event in session.listen(
            PageEvent.SCREENCAST_VISIBILITY_CHANGED,
            ScreencastVisibilityChangedEvent,
        ):
            await events.put(VisibilityChanged(target_id, event.visible))

    async def _listen_target_created(
        self,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        async for event in self._client.listen(
            TargetEvent.TARGET_CREATED,
            TargetCreatedEvent,
        ):
            if event.target_info.type == "page":
                await events.put(TargetAdded(event.target_info.target_id))

    async def _listen_target_destroyed(
        self,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        async for event in self._client.listen(
            TargetEvent.TARGET_DESTROYED,
            TargetDestroyedEvent,
        ):
            await events.put(TargetRemoved(event.target_id))

    async def _listen_target_crashed(
        self,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        async for event in self._client.listen(
            TargetEvent.TARGET_CRASHED,
            TargetCrashedEvent,
        ):
            await events.put(TargetRemoved(event.target_id))

    async def _listen_target_detached(
        self,
        events: asyncio.Queue[StreamEvent],
    ) -> None:
        async for event in self._client.listen(
            TargetEvent.DETACHED_FROM_TARGET,
            DetachedFromTargetEvent,
        ):
            if event.target_id is not None:
                await events.put(TargetDetached(event.target_id))


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
