import asyncio
from collections.abc import Awaitable, Callable

from cdpify import Client
from cdpify.domains.target.events import (
    DetachedFromTargetEvent,
    TargetCrashedEvent,
    TargetCreatedEvent,
    TargetDestroyedEvent,
    TargetEvent,
    TargetInfoChangedEvent,
)

from backend.features.browser_tunnel.application import TargetCrashed
from backend.features.browser_tunnel.infrastructure.events.stream import PublishEvent


class TargetEventBridge:
    def __init__(
        self,
        publish: PublishEvent,
        changed: Callable[[str | None], Awaitable[None]],
        detached: Callable[[str | None, str | None], Awaitable[None]],
        failed: Callable[[], None],
    ) -> None:
        self._publish = publish
        self._changed = changed
        self._detached = detached
        self._failed = failed
        self._target_tasks: set[asyncio.Task[None]] = set()

    async def start(self, client: Client) -> None:
        if self._target_tasks:
            return
        self._target_tasks = {
            self._task(self._listen_target_created(client), TargetEvent.TARGET_CREATED),
            self._task(
                self._listen_target_destroyed(client), TargetEvent.TARGET_DESTROYED
            ),
            self._task(
                self._listen_target_info_changed(client),
                TargetEvent.TARGET_INFO_CHANGED,
            ),
            self._task(self._listen_target_crashed(client), TargetEvent.TARGET_CRASHED),
            self._task(
                self._listen_target_detached(client),
                TargetEvent.DETACHED_FROM_TARGET,
            ),
        }
        await asyncio.sleep(0)

    async def stop(self) -> None:
        await self._stop_tasks(self._target_tasks)

    async def _listen_target_created(self, client: Client) -> None:
        async for event in client.listen(
            TargetEvent.TARGET_CREATED, TargetCreatedEvent
        ):
            if event.target_info.type == "page":
                await self._changed(None)

    async def _listen_target_destroyed(self, client: Client) -> None:
        async for event in client.listen(
            TargetEvent.TARGET_DESTROYED, TargetDestroyedEvent
        ):
            await self._detached(event.target_id, None)
            await self._changed(None)

    async def _listen_target_info_changed(self, client: Client) -> None:
        async for event in client.listen(
            TargetEvent.TARGET_INFO_CHANGED, TargetInfoChangedEvent
        ):
            if event.target_info.type != "page":
                continue
            await self._changed(event.target_info.target_id)

    async def _listen_target_crashed(self, client: Client) -> None:
        async for event in client.listen(
            TargetEvent.TARGET_CRASHED, TargetCrashedEvent
        ):
            self._publish(
                TargetCrashed(event.target_id, event.status, event.error_code)
            )

    async def _listen_target_detached(self, client: Client) -> None:
        async for event in client.listen(
            TargetEvent.DETACHED_FROM_TARGET, DetachedFromTargetEvent
        ):
            await self._detached(event.target_id, event.session_id)

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
