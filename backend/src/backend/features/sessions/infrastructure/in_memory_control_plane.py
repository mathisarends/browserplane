from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.features.sessions.application.exceptions import (
    SessionExpiredException,
    SessionNotFoundException,
)
from backend.features.sessions.application.models import (
    BrowserEndpoints,
    BrowserSummary,
    Lease,
)
from backend.features.sessions.application.ports import BrowserCatalog, LeaseBroker
from backend.settings import BackendSettings


class InMemoryControlPlane(BrowserCatalog, LeaseBroker):
    """Stand-in for the control plane so the backend runs on its own.

    Replaced by an adapter over the generated control-plane client; the ports it
    implements are what that adapter has to satisfy.
    """

    def __init__(self, settings: BackendSettings) -> None:
        self._endpoints = {
            endpoints.browser_id: endpoints for endpoints in settings.endpoints()
        }
        self._leases: dict[UUID, Lease] = {}

    async def list(self) -> Sequence[BrowserSummary]:
        leased = {lease.browser_id for lease in self._live_leases()}
        return [
            BrowserSummary(id=browser_id, is_available=browser_id not in leased)
            for browser_id in self._endpoints
        ]

    async def endpoints(self, browser_id: UUID) -> BrowserEndpoints:
        endpoints = self._endpoints.get(browser_id)
        if endpoints is None:
            raise SessionNotFoundException("Unknown browser")
        return endpoints

    async def create(self, browser_id: UUID, owner_id: UUID, ttl: timedelta) -> Lease:
        now = datetime.now(UTC)
        lease = Lease(
            id=uuid4(),
            browser_id=browser_id,
            owner_id=owner_id,
            expires_at=now + ttl,
            created_at=now,
        )
        self._leases[lease.id] = lease
        return lease

    async def get(self, lease_id: UUID) -> Lease:
        lease = self._leases.get(lease_id)
        if lease is None:
            raise SessionNotFoundException()
        if lease.expires_at <= datetime.now(UTC):
            del self._leases[lease_id]
            raise SessionExpiredException()
        return lease

    async def release(self, lease_id: UUID) -> None:
        if self._leases.pop(lease_id, None) is None:
            raise SessionNotFoundException()

    def _live_leases(self) -> list[Lease]:
        now = datetime.now(UTC)
        return [lease for lease in self._leases.values() if lease.expires_at > now]
