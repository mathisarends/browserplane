import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.models import Lease
from backend.features.leases.application.ports import BrowserAllocator, LeaseStore

logger = logging.getLogger(__name__)


class LeaseService:
    """Lease lifecycle on top of an opaque browser allocator."""

    def __init__(self, allocator: BrowserAllocator, store: LeaseStore) -> None:
        self._allocator = allocator
        self._store = store
        self._lock = asyncio.Lock()

    async def create(
        self,
        browser_id: UUID,
        owner_id: UUID,
        ttl: timedelta,
        lease_id: UUID | None = None,
    ) -> Lease:
        """Claim a browser, optionally under an id the caller already handed out."""
        async with self._lock:
            await self._expire()
            await self._allocator.reserve(browser_id)
            now = datetime.now(UTC)
            lease = Lease(
                id=lease_id or uuid4(),
                browser_id=browser_id,
                owner_id=owner_id,
                expires_at=now + ttl,
                created_at=now,
            )
            await self._store.add(lease)
            logger.info(
                "Lease created lease_id=%s browser_id=%s owner_id=%s expires_at=%s",
                lease.id,
                lease.browser_id,
                lease.owner_id,
                lease.expires_at.isoformat(),
            )
            return lease

    async def list(self) -> tuple[Lease, ...]:
        """Every lease still standing, newest first; expired ones are dropped."""
        async with self._lock:
            await self._expire()
            return tuple(
                sorted(
                    await self._store.list(),
                    key=lambda lease: lease.created_at,
                    reverse=True,
                )
            )

    async def get(self, lease_id: UUID) -> Lease:
        async with self._lock:
            await self._expire()
            lease = await self._store.get(lease_id)
            if lease is None:
                logger.warning(
                    "Lease lookup failed lease_id=%s active_lease_count=%d",
                    lease_id,
                    len(await self._store.list()),
                )
                raise LeaseNotFoundException()
            return lease

    async def release(self, lease_id: UUID, *, reason: str = "requested") -> None:
        async with self._lock:
            lease = await self._store.get(lease_id)
            if lease is None:
                logger.warning(
                    "Lease release skipped because it no longer exists "
                    "lease_id=%s reason=%s",
                    lease_id,
                    reason,
                )
                raise LeaseNotFoundException()
            await self._store.remove(lease.id)
            await self._allocator.release(lease.browser_id)
            logger.info(
                "Lease released lease_id=%s browser_id=%s reason=%s",
                lease.id,
                lease.browser_id,
                reason,
            )

    async def _expire(self) -> None:
        now = datetime.now(UTC)
        for lease in await self._store.list():
            if lease.is_expired(now):
                await self._store.remove(lease.id)
                await self._allocator.release(lease.browser_id)
                logger.info(
                    "Lease expired lease_id=%s browser_id=%s expires_at=%s",
                    lease.id,
                    lease.browser_id,
                    lease.expires_at.isoformat(),
                )
