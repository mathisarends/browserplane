from datetime import datetime, timedelta
from uuid import UUID

from backend.features.leases.application.ports import LeaseStore
from backend.features.leases.domain.models import Lease


class InMemoryLeaseStore(LeaseStore):
    """Process-local LeaseStore implementation for the current MVP."""

    def __init__(self) -> None:
        self._leases: dict[UUID, Lease] = {}

    async def save(self, lease: Lease) -> Lease:
        self._leases[lease.id] = lease
        return lease

    async def list_current(self) -> tuple[Lease, ...]:
        return tuple(
            lease for lease in self._leases.values() if lease.state != "released"
        )

    async def get(self, lease_id: UUID, *, for_update: bool = False) -> Lease | None:
        return self._leases.get(lease_id)

    async def claim_due(
        self, now: datetime, *, limit: int, reason: str
    ) -> tuple[Lease, ...]:
        due = [lease for lease in self._leases.values() if lease.is_reclaimable(now)]
        claimed = tuple(
            lease.begin_reclaim(now, reason=reason) for lease in due[:limit]
        )
        for lease in claimed:
            self._leases[lease.id] = lease
        return claimed

    async def renew(
        self,
        lease_id: UUID,
        *,
        now: datetime,
        ttl: timedelta,
        grace_period: timedelta,
    ) -> Lease | None:
        lease = self._leases.get(lease_id)
        if lease is None:
            return None
        try:
            lease = lease.renew(
                now,
                expires_at=now + ttl,
                reclaim_after=now + ttl + grace_period,
            )
        except ValueError:
            return None
        self._leases[lease.id] = lease
        return lease
