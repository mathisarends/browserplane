from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class LeaseState(StrEnum):
    ACTIVE = "active"
    RECLAIMING = "reclaiming"
    RELEASED = "released"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Lease:
    """Time-boxed, exclusive claim of one browser by one owner."""

    id: UUID
    browser_id: UUID
    owner_id: UUID
    generation: int
    state: LeaseState
    last_renewed_at: datetime
    expires_at: datetime
    reclaim_after: datetime
    created_at: datetime
    reclaim_started_at: datetime | None = None
    released_at: datetime | None = None
    release_reason: str | None = None
    cleanup_attempts: int = 0
    cleanup_retry_at: datetime | None = None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def is_reclaimable(self, now: datetime) -> bool:
        if self.state is LeaseState.ACTIVE:
            return self.reclaim_after <= now
        return (
            self.state is LeaseState.FAILED
            and self.cleanup_retry_at is not None
            and self.cleanup_retry_at <= now
        )

    def renew(
        self, now: datetime, *, expires_at: datetime, reclaim_after: datetime
    ) -> Lease:
        if self.state is not LeaseState.ACTIVE or self.reclaim_after <= now:
            raise ValueError("Lease can no longer be renewed")
        return replace(
            self,
            last_renewed_at=now,
            expires_at=expires_at,
            reclaim_after=reclaim_after,
        )

    def begin_reclaim(self, now: datetime, *, reason: str) -> Lease:
        if self.state not in (LeaseState.ACTIVE, LeaseState.FAILED):
            return self
        return replace(
            self,
            state=LeaseState.RECLAIMING,
            reclaim_started_at=now,
            release_reason=reason,
            cleanup_attempts=self.cleanup_attempts + 1,
            cleanup_retry_at=None,
        )

    def released(self, now: datetime) -> Lease:
        return replace(
            self,
            state=LeaseState.RELEASED,
            released_at=now,
            cleanup_retry_at=None,
        )

    def cleanup_failed(self, retry_at: datetime) -> Lease:
        return replace(
            self,
            state=LeaseState.FAILED,
            cleanup_retry_at=retry_at,
        )
