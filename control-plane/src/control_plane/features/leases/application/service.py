import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from control_plane.features.leases.application.exceptions import LeaseNotFoundException
from control_plane.features.leases.application.models import Lease
from control_plane.features.leases.application.ports import BrowserAllocator, LeaseStore


class LeaseService:
    """Lease lifecycle on top of an opaque browser allocator."""

    def __init__(self, allocator: BrowserAllocator, store: LeaseStore) -> None:
        self._allocator = allocator
        self._store = store
        self._lock = asyncio.Lock()

    async def create(self, browser_id: UUID, owner_id: UUID, ttl: timedelta) -> Lease:
        async with self._lock:
            await self._expire()
            await self._allocator.reserve(browser_id)
            now = datetime.now(UTC)
            lease = Lease(
                id=uuid4(),
                browser_id=browser_id,
                owner_id=owner_id,
                expires_at=now + ttl,
                created_at=now,
            )
            self._store.add(lease)
            return lease

    async def get(self, lease_id: UUID) -> Lease:
        async with self._lock:
            await self._expire()
            lease = self._store.get(lease_id)
            if lease is None:
                raise LeaseNotFoundException()
            return lease

    async def release(self, lease_id: UUID) -> None:
        async with self._lock:
            lease = self._store.get(lease_id)
            if lease is None:
                raise LeaseNotFoundException()
            self._store.remove(lease.id)
            await self._allocator.release(lease.browser_id)

    async def _expire(self) -> None:
        now = datetime.now(UTC)
        for lease in self._store.list():
            if lease.is_expired(now):
                self._store.remove(lease.id)
                await self._allocator.release(lease.browser_id)
