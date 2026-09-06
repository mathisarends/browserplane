from abc import ABC, abstractmethod
from uuid import UUID

from backend.features.leases.application.models import Lease


class LeaseStore(ABC):
    """Storage port for active leases."""

    @abstractmethod
    async def add(self, lease: Lease) -> None: ...

    @abstractmethod
    async def list(self) -> tuple[Lease, ...]: ...

    @abstractmethod
    async def get(self, lease_id: UUID) -> Lease | None: ...

    @abstractmethod
    async def remove(self, lease_id: UUID) -> None: ...


class BrowserAllocator(ABC):
    """Reserves and releases browsers on behalf of the lease lifecycle."""

    @abstractmethod
    async def reserve(self, browser_id: UUID) -> None: ...

    @abstractmethod
    async def release(self, browser_id: UUID) -> None: ...
