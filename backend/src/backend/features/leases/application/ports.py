from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from uuid import UUID

from backend.features.leases.domain.models import Lease


class LeaseStore(ABC):
    """Storage port for active leases."""

    @abstractmethod
    async def save(self, lease: Lease) -> Lease: ...

    @abstractmethod
    async def list_current(self) -> tuple[Lease, ...]: ...

    @abstractmethod
    async def get(
        self, lease_id: UUID, *, for_update: bool = False
    ) -> Lease | None: ...

    @abstractmethod
    async def claim_due(
        self, now: datetime, *, limit: int, reason: str
    ) -> tuple[Lease, ...]: ...

    @abstractmethod
    async def renew(
        self,
        lease_id: UUID,
        *,
        now: datetime,
        ttl: timedelta,
        grace_period: timedelta,
    ) -> Lease | None: ...


class BrowserAllocator(ABC):
    """Reserves and releases browsers on behalf of the lease lifecycle."""

    @abstractmethod
    async def reserve(self, browser_id: UUID) -> int:
        """Reserve the browser and return its new fencing generation."""

    @abstractmethod
    async def recycle(self, browser_id: UUID) -> None: ...
