import random
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID


class LeaseState(StrEnum):
    ACTIVE = "active"
    RECLAIMING = "reclaiming"
    RELEASED = "released"
    FAILED = "failed"
    # Cleanup and worker replacement both ran out; nothing retries this on its
    # own any more. The browser stays unschedulable until someone looks at it.
    QUARANTINED = "quarantined"


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
            # The first attempt dates the reclaim. Retries share its deadline,
            # so a stuck worker cannot renew its own recovery budget.
            reclaim_started_at=self.reclaim_started_at or now,
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

    def quarantined(self) -> Lease:
        """Stop recovering this lease; both cleanup and replacement failed."""
        return replace(
            self,
            state=LeaseState.QUARANTINED,
            cleanup_retry_at=None,
        )


@dataclass(frozen=True, slots=True)
class CleanupRetryPolicy:
    """How long a failed reclaim is retried before the worker gets replaced.

    Retries exist for the transient failure: a worker that is busy, restarting
    or briefly unreachable. Past these bounds, waiting longer only keeps the
    slot occupied, so recovery escalates instead of repeating itself.
    """

    base_delay: timedelta
    max_delay: timedelta
    max_attempts: int
    max_duration: timedelta

    def is_exhausted(self, lease: Lease, *, now: datetime) -> bool:
        if lease.cleanup_attempts >= self.max_attempts:
            return True
        started_at = lease.reclaim_started_at
        return started_at is not None and now - started_at >= self.max_duration

    def retry_at(self, lease: Lease, *, now: datetime) -> datetime:
        """Back off exponentially, jittered so retries never march in step."""
        attempts_so_far = max(lease.cleanup_attempts - 1, 0)
        delay = min(self.base_delay * 2**attempts_so_far, self.max_delay)
        return now + delay * random.uniform(0.5, 1.0)
