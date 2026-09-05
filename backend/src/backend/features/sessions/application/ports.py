from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from backend.features.sessions.application.models import (
    BrowserEndpoints,
    BrowserSummary,
    Lease,
)


class BrowserCatalog(ABC):
    """Read model of the browser pool owned by the control plane."""

    @abstractmethod
    async def list(self) -> Sequence[BrowserSummary]: ...

    @abstractmethod
    async def endpoints(self, browser_id: UUID) -> BrowserEndpoints: ...


class LeaseBroker(ABC):
    """Lease lifecycle as offered by the control plane."""

    @abstractmethod
    async def create(
        self, browser_id: UUID, owner_id: UUID, ttl: timedelta
    ) -> Lease: ...

    @abstractmethod
    async def get(self, lease_id: UUID) -> Lease: ...

    @abstractmethod
    async def release(self, lease_id: UUID) -> None: ...
