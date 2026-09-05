import asyncio
import base64
import logging
from collections.abc import AsyncGenerator
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

from browser_worker.features.screencast.application.models import ScreencastOptions
from browser_worker.features.screencast.infrastructure.events import (
    Frame,
    StreamEvent,
    TargetAdded,
    TargetDetached,
    TargetRemoved,
    VisibilityChanged,
    VisibleTarget,
)
from browser_worker.features.screencast.infrastructure.tasks import (
    cancel_and_wait,
)

logger = logging.getLogger(__name__)


class ActiveTabBridge:
    """Track which page Chromium shows and stream that page's frames.

    CDP only reports page visibility while a screencast runs on the page, so
    every page target is screencast and the visible one decides what is
    published. Both the live screencast and the recorder consume these updates.
    """

    def __init__(self, client: Client, options: ScreencastOptions) -> None:
        self._client = client
        self._options = options
        self._events: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._page_tasks: dict[str, asyncio.Task[None]] = {}
        self._visible_target = VisibleTarget()

    async def frames(self) -> AsyncGenerator[bytes]:
        target_listeners = self._start_target_listeners()
        try:
            await self._discover_existing_pages()
            while True:
                frame = await self._handle_next_event()
                if frame is not None:
                    yield frame
        finally:
            await cancel_and_wait(*target_listeners, *self._page_tasks.values())

    def _start_target_listeners(self) -> tuple[asyncio.Task[None], ...]:
        return (
            asyncio.create_task(self._listen_target_created()),
            asyncio.create_task(self._listen_target_destroyed()),
            asyncio.create_task(self._listen_target_crashed()),
            asyncio.create_task(self._listen_target_detached()),
        )

    async def _discover_existing_pages(self) -> None:
        # Give the listener tasks a chance to subscribe before discovery starts.
        await asyncio.sleep(0)
        await self._client.target.set_discover_targets(discover=True)
        targets = await self._client.target.get_targets()
        for target in targets.target_infos:
            if target.type == "page":
                self._start_page(target.target_id)

    async def _handle_next_event(self) -> bytes | None:
        match await self._events.get():
            case TargetAdded(target_id=target_id):
                self._start_page(target_id)
            case TargetRemoved(target_id=target_id):
                await self._remove_page(target_id)
            case TargetDetached(target_id=target_id):
                await self._reattach_page_if_present(target_id)
            case VisibilityChanged(target_id=target_id, visible=visible):
                self._visible_target.change_visibility(target_id, visible=visible)
            case Frame() as frame:
                return self._visible_target.frame(frame)
        return None

    def _start_page(self, target_id: str) -> None:
        if target_id in self._page_tasks:
            return
        self._page_tasks[target_id] = asyncio.create_task(
            self._capture_page(target_id),
            name=f"screencast:{target_id}",
        )

    async def _remove_page(self, target_id: str) -> None:
        task = self._page_tasks.pop(target_id, None)
        if task is not None:
            await cancel_and_wait(task)
        self._visible_target.remove(target_id)

    async def _reattach_page_if_present(self, target_id: str) -> None:
        await self._remove_page(target_id)
        targets = await self._client.target.get_targets()
        if any(
            target.type == "page" and target.target_id == target_id
            for target in targets.target_infos
        ):
            self._start_page(target_id)

    async def _capture_page(self, target_id: str) -> None:
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
                asyncio.create_task(self._listen_frames(session, target_id)),
                asyncio.create_task(self._listen_visibility(session, target_id)),
            )
            await asyncio.sleep(0)
            await session.page.start_screencast(
                format="jpeg",
                quality=self._options.quality,
                max_width=self._options.width,
                max_height=self._options.height,
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
            await cancel_and_wait(*listeners)
            if session is not None:
                with suppress(Exception):
                    await session.page.stop_screencast()
                with suppress(Exception):
                    await self._client.target.detach_from_target(
                        session_id=session.session_id
                    )

    async def _listen_frames(self, session: CDPSession, target_id: str) -> None:
        async for event in session.listen(
            PageEvent.SCREENCAST_FRAME,
            ScreencastFrameEvent,
        ):
            try:
                data = base64.b64decode(event.data)
                await self._events.put(Frame(target_id, data))
            finally:
                await session.page.screencast_frame_ack(session_id=event.session_id)

    async def _listen_visibility(
        self,
        session: CDPSession,
        target_id: str,
    ) -> None:
        async for event in session.listen(
            PageEvent.SCREENCAST_VISIBILITY_CHANGED,
            ScreencastVisibilityChangedEvent,
        ):
            await self._events.put(VisibilityChanged(target_id, event.visible))

    async def _listen_target_created(self) -> None:
        async for event in self._client.listen(
            TargetEvent.TARGET_CREATED,
            TargetCreatedEvent,
        ):
            if event.target_info.type == "page":
                await self._events.put(TargetAdded(event.target_info.target_id))

    async def _listen_target_destroyed(self) -> None:
        async for event in self._client.listen(
            TargetEvent.TARGET_DESTROYED,
            TargetDestroyedEvent,
        ):
            await self._events.put(TargetRemoved(event.target_id))

    async def _listen_target_crashed(self) -> None:
        async for event in self._client.listen(
            TargetEvent.TARGET_CRASHED,
            TargetCrashedEvent,
        ):
            await self._events.put(TargetRemoved(event.target_id))

    async def _listen_target_detached(self) -> None:
        async for event in self._client.listen(
            TargetEvent.DETACHED_FROM_TARGET,
            DetachedFromTargetEvent,
        ):
            if event.target_id is not None:
                await self._events.put(TargetDetached(event.target_id))
