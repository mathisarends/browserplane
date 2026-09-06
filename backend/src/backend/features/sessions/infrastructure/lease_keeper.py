import asyncio
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from dishka import AsyncContainer, Scope

from backend.features.sessions.application.service import SessionService
from backend.features.sessions.domain.models import ResolvedSession

logger = logging.getLogger(__name__)


class SessionLeaseKeeper:
    """Keep a lease alive while one long-running control operation is active."""

    def __init__(
        self,
        container: AsyncContainer,
        heartbeat_interval_seconds: int,
    ) -> None:
        self._container = container
        self._heartbeat_interval_seconds = heartbeat_interval_seconds

    async def resolve(
        self, session_id: UUID, *, renew: bool = False
    ) -> ResolvedSession:
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
        logger.info(
            "Session heartbeat started session_id=%s interval_seconds=%d",
            session_id,
            self._heartbeat_interval_seconds,
        )
        beat = 0
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval_seconds)
                beat += 1
                session = await self.resolve(session_id, renew=True)
                logger.info(
                    "Session heartbeat session_id=%s beat=%d browser_id=%s "
                    "generation=%s expires_at=%s ttl_seconds=%.1f",
                    session_id,
                    beat,
                    session.browser_id,
                    session.lease_generation,
                    session.expires_at.isoformat() if session.expires_at else None,
                    _remaining_seconds(session),
                )
        except asyncio.CancelledError:
            logger.info(
                "Session heartbeat stopped session_id=%s beats=%d", session_id, beat
            )
            raise
        except Exception as error:
            logger.warning(
                "Session heartbeat failed session_id=%s beats=%d error_type=%s",
                session_id,
                beat,
                type(error).__name__,
            )
            raise


def _remaining_seconds(session: ResolvedSession) -> float:
    if session.expires_at is None:
        return 0.0
    return (session.expires_at - datetime.now(UTC)).total_seconds()
