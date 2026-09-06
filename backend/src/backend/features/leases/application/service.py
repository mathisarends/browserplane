import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.ports import BrowserAllocator, LeaseStore
from backend.features.leases.domain.models import Lease, LeaseState
from backend.features.leases.settings import LeaseSettings

logger = logging.getLogger(__name__)


class LeaseService:
    """Persisted, renewable browser claims with an idempotent reclaim path."""

    def __init__(
        self,
        allocator: BrowserAllocator,
        store: LeaseStore,
        settings: LeaseSettings,
    ) -> None:
        self._allocator = allocator
        self._store = store
        self._ttl = timedelta(seconds=settings.ttl_seconds)
        self._grace_period = timedelta(seconds=settings.grace_period_seconds)
        self._reaper_batch_size = settings.reaper_batch_size
        self._cleanup_retry = timedelta(seconds=settings.cleanup_retry_seconds)

    async def create(
        self,
        browser_id: UUID,
        owner_id: UUID,
        lease_id: UUID | None = None,
    ) -> Lease:
        """Claim a row-locked browser under a new fencing generation."""
        generation = await self._allocator.reserve(browser_id)
        now = datetime.now(UTC)
        lease = Lease(
            id=lease_id or uuid4(),
            browser_id=browser_id,
            owner_id=owner_id,
            generation=generation,
            state=LeaseState.ACTIVE,
            last_renewed_at=now,
            expires_at=now + self._ttl,
            reclaim_after=now + self._ttl + self._grace_period,
            created_at=now,
        )
        await self._store.save(lease)
        logger.info(
            "Lease created lease_id=%s browser_id=%s generation=%d "
            "expires_at=%s reclaim_after=%s",
            lease.id,
            lease.browser_id,
            lease.generation,
            lease.expires_at.isoformat(),
            lease.reclaim_after.isoformat(),
        )
        return lease

    async def list(self) -> tuple[Lease, ...]:
        return await self._store.list_current()

    async def inspect(self, lease_id: UUID) -> Lease:
        lease = await self._store.get(lease_id)
        if lease is None or lease.state is LeaseState.RELEASED:
            raise LeaseNotFoundException()
        return lease

    async def get(self, lease_id: UUID) -> Lease:
        """Return only a lease that may currently issue browser operations."""
        lease = await self.inspect(lease_id)
        if lease.state is not LeaseState.ACTIVE or lease.is_expired(datetime.now(UTC)):
            raise LeaseNotFoundException()
        return lease

    async def renew(self, lease_id: UUID) -> Lease:
        now = datetime.now(UTC)
        lease = await self._store.renew(
            lease_id,
            now=now,
            ttl=self._ttl,
            grace_period=self._grace_period,
        )
        if lease is None:
            raise LeaseNotFoundException()
        logger.debug(
            "Lease renewed lease_id=%s browser_id=%s generation=%d expires_at=%s",
            lease.id,
            lease.browser_id,
            lease.generation,
            lease.expires_at.isoformat(),
        )
        return lease

    async def release(self, lease_id: UUID, *, reason: str = "requested") -> None:
        now = datetime.now(UTC)
        lease = await self._store.get(lease_id, for_update=True)
        if lease is None:
            raise LeaseNotFoundException()
        if lease.state is LeaseState.RELEASED:
            return
        if lease.state is not LeaseState.RECLAIMING:
            lease = await self._store.save(lease.begin_reclaim(now, reason=reason))
        logger.info(
            "Lease reclaim started lease_id=%s browser_id=%s generation=%d reason=%s",
            lease.id,
            lease.browser_id,
            lease.generation,
            reason,
        )
        await self._finish_reclaim(lease)

    async def reap_due(self) -> tuple[UUID, ...]:
        now = datetime.now(UTC)
        leases = await self._store.claim_due(
            now,
            limit=self._reaper_batch_size,
            reason="lease_expired",
        )
        if leases:
            logger.info(
                "Lease reaper claimed %d expired lease(s) lease_ids=%s",
                len(leases),
                ",".join(str(lease.id) for lease in leases),
            )
        released: list[UUID] = []
        for lease in leases:
            if await self._finish_reclaim(lease):
                released.append(lease.id)
        return tuple(released)

    async def _finish_reclaim(self, lease: Lease) -> bool:
        try:
            await self._allocator.recycle(lease.browser_id)
        except Exception as error:
            failed = lease.cleanup_failed(datetime.now(UTC) + self._cleanup_retry)
            await self._store.save(failed)
            logger.exception(
                "Lease cleanup failed lease_id=%s browser_id=%s generation=%d "
                "attempt=%d error_type=%s",
                lease.id,
                lease.browser_id,
                lease.generation,
                lease.cleanup_attempts,
                type(error).__name__,
            )
            return False
        await self._store.save(lease.released(datetime.now(UTC)))
        logger.info(
            "Lease released lease_id=%s browser_id=%s generation=%d reason=%s",
            lease.id,
            lease.browser_id,
            lease.generation,
            lease.release_reason,
        )
        return True
