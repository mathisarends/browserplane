import asyncio
import logging
from collections.abc import Awaitable, Callable

from cdpify import CDPSession
from cdpify.domains.network.events import LoadingFailedEvent, NetworkEvent
from cdpify.domains.page.events import (
    DomContentEventFiredEvent,
    FrameNavigatedEvent,
    FrameStartedLoadingEvent,
    FrameStoppedLoadingEvent,
    NavigatedWithinDocumentEvent,
    PageEvent,
)
from cdpify.exceptions import CDPCommandException

from backend.features.browser_tunnel.application import (
    BrowserPageMetadata,
    BrowserTab,
    NavigationChanged,
)
from backend.features.browser_tunnel.infrastructure.events.stream import PublishEvent

logger = logging.getLogger(__name__)


class PageEventBridge:
    def __init__(
        self,
        session: CDPSession,
        target_id: str,
        page_metadata: BrowserPageMetadata,
        tabs: Callable[[], Awaitable[list[BrowserTab]]],
        publish: PublishEvent,
        failed: Callable[[], None],
    ) -> None:
        self._session = session
        self._target_id = target_id
        self._page_metadata = page_metadata
        self._tabs = tabs
        self._publish = publish
        self._failed = failed
        self._main_frame_id: str | None = None
        self._loading = False
        self._can_go_back = False
        self._can_go_forward = False
        self._favicon_url: str | None = None
        self._page_tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        frame_tree = await self._session.page.get_frame_tree()
        self._main_frame_id = frame_tree.frame_tree.frame.id
        self._page_tasks = {
            self._task(
                self._listen_frame_navigated(self._session), PageEvent.FRAME_NAVIGATED
            ),
            self._task(
                self._listen_navigated_within_document(self._session),
                PageEvent.NAVIGATED_WITHIN_DOCUMENT,
            ),
            self._task(
                self._listen_frame_started_loading(self._session),
                PageEvent.FRAME_STARTED_LOADING,
            ),
            self._task(
                self._listen_frame_stopped_loading(self._session),
                PageEvent.FRAME_STOPPED_LOADING,
            ),
            self._task(
                self._listen_dom_content_event_fired(self._session),
                PageEvent.DOM_CONTENT_EVENT_FIRED,
            ),
            self._task(
                self._listen_loading_failed(self._session), NetworkEvent.LOADING_FAILED
            ),
        }
        await asyncio.sleep(0)

    async def stop(self) -> None:
        await self._stop_tasks(self._page_tasks)

    async def current_navigation(self) -> NavigationChanged | None:
        return await self._navigation_event(refresh_metadata=True)

    async def _listen_frame_navigated(self, session: CDPSession) -> None:
        async for event in session.listen(
            PageEvent.FRAME_NAVIGATED, FrameNavigatedEvent
        ):
            if event.frame.parent_id is None:
                self._main_frame_id = event.frame.id
                self._favicon_url = None
                await self._dispatch_navigation()

    async def _listen_navigated_within_document(self, session: CDPSession) -> None:
        async for event in session.listen(
            PageEvent.NAVIGATED_WITHIN_DOCUMENT,
            NavigatedWithinDocumentEvent,
        ):
            if event.frame_id == self._main_frame_id:
                await self._dispatch_navigation()

    async def _listen_frame_started_loading(self, session: CDPSession) -> None:
        async for event in session.listen(
            PageEvent.FRAME_STARTED_LOADING, FrameStartedLoadingEvent
        ):
            if event.frame_id == self._main_frame_id:
                self._loading = True
                await self._dispatch_navigation()

    async def _listen_frame_stopped_loading(self, session: CDPSession) -> None:
        async for event in session.listen(
            PageEvent.FRAME_STOPPED_LOADING, FrameStoppedLoadingEvent
        ):
            if event.frame_id == self._main_frame_id:
                self._loading = False
                await self._dispatch_navigation(refresh_metadata=True)

    async def _listen_dom_content_event_fired(self, session: CDPSession) -> None:
        async for _ in session.listen(
            PageEvent.DOM_CONTENT_EVENT_FIRED, DomContentEventFiredEvent
        ):
            await self._dispatch_navigation(refresh_metadata=True)

    async def _listen_loading_failed(self, session: CDPSession) -> None:
        async for event in session.listen(
            NetworkEvent.LOADING_FAILED, LoadingFailedEvent
        ):
            if event.type == "Document" and not event.canceled:
                self._loading = False
                await self._dispatch_navigation(error=event.error_text)

    async def _dispatch_navigation(
        self, *, error: str | None = None, refresh_metadata: bool = False
    ) -> None:
        event = await self._navigation_event(
            error=error, refresh_metadata=refresh_metadata
        )
        if event is not None:
            self._publish(event)

    async def _navigation_event(
        self, *, error: str | None = None, refresh_metadata: bool = False
    ) -> NavigationChanged | None:
        target_id = self._target_id
        tab = next((tab for tab in await self._tabs() if tab.id == target_id), None)
        if tab is None:
            return None
        try:
            history = await self._session.page.get_navigation_history()
        except CDPCommandException:
            logger.debug(
                "Navigation history is temporarily unavailable for %s", target_id
            )
        else:
            self._can_go_back = history.current_index > 0
            self._can_go_forward = history.current_index < len(history.entries) - 1
        if refresh_metadata:
            self._favicon_url = await self._page_metadata.favicon_url()
        return NavigationChanged(
            tab_id=target_id,
            title=tab.title,
            url=tab.url,
            loading=self._loading,
            can_go_back=self._can_go_back,
            can_go_forward=self._can_go_forward,
            favicon_url=self._favicon_url,
            error=error,
        )

    def _task(self, coroutine, event_name: str) -> asyncio.Task[None]:
        task = asyncio.create_task(
            coroutine,
            name=f"browser-events:{event_name}",
        )
        task.add_done_callback(self._task_finished)
        return task

    def _task_finished(self, task: asyncio.Task[None]) -> None:
        if not task.cancelled() and task.exception() is not None:
            self._failed()

    @staticmethod
    async def _stop_tasks(tasks: set[asyncio.Task[None]]) -> None:
        pending = tuple(tasks)
        tasks.clear()
        for task in pending:
            if not task.done():
                task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
