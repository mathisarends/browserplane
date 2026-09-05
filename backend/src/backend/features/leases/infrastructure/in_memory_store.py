from uuid import UUID

from backend.features.leases.application.models import Lease
from backend.features.leases.application.ports import LeaseStore


class InMemoryLeaseStore(LeaseStore):
    """Process-local LeaseStore implementation for the current MVP."""

    def __init__(self) -> None:
        self._leases: dict[UUID, Lease] = {}

    def add(self, lease: Lease) -> None:
        self._leases[lease.id] = lease

    def list(self) -> list[Lease]:
        return list(self._leases.values())

    def get(self, lease_id: UUID) -> Lease | None:
        return self._leases.get(lease_id)

    def remove(self, lease_id: UUID) -> None:
        self._leases.pop(lease_id, None)
