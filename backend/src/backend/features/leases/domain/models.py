from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Lease:
    """Time-boxed, exclusive claim of one browser by one owner."""

    id: UUID
    browser_id: UUID
    owner_id: UUID
    expires_at: datetime
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now
