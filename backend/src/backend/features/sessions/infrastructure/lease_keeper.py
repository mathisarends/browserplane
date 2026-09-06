import asyncio
from collections.abc import Awaitable
from typing import Any
from uuid import UUID

from dishka import AsyncContainer, Scope

from backend.features.sessions.application.service import SessionService
from backend.features.sessions.domain.models import ActiveSession


class SessionLeaseKeeper:
    """Keep a lease alive while one long-running control operation is active."""

    def __init__(
        self,
        container: AsyncContainer,
        heartbeat_interval_seconds: int,
    ) -> None:
        self._container = container
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    async def resolve(self, session_id: UUID, *, renew: bool = False) -> ActiveSession:
        """Resolve one session in a short unit of work outside the live stream."""
        async with self._container(scope=Scope.REQUEST) as scoped:
            service = await scoped.get(SessionService)
            if renew:
                return await service.renew(session_id)
            return await service.get_active(session_id)

    async def run(
        self,
        session_id: UUID,
        operation: Awaitable[Any],
    ) -> None:
        tasks = {
            asyncio.ensure_future(operation),
            asyncio.create_task(self._keep_alive(session_id)),
        }
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _keep_alive(self, session_id: UUID) -> None:
        while True:
            await asyncio.sleep(self._heartbeat_interval_seconds)
            async with self._container(scope=Scope.REQUEST) as scoped:
                service = await scoped.get(SessionService)
                await service.renew(session_id)
