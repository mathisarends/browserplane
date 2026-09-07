from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from backend.features.leases.domain.models import (
    CleanupRetryPolicy,
    Lease,
    LeaseState,
)


def _lease(*, state: LeaseState = LeaseState.ACTIVE) -> Lease:
    now = datetime.now(UTC)
    return Lease(
        id=uuid4(),
        browser_id=uuid4(),
        owner_id=uuid4(),
        generation=2,
        state=state,
        created_at=now,
        last_renewed_at=now,
        expires_at=now + timedelta(minutes=1),
        reclaim_after=now + timedelta(minutes=2),
    )


def test_active_lease_renews_until_its_reclaim_deadline() -> None:
    lease = _lease()
    now = datetime.now(UTC)

    renewed = lease.renew(
        now,
        expires_at=now + timedelta(minutes=3),
        reclaim_after=now + timedelta(minutes=4),
    )

    assert renewed.last_renewed_at == now
    assert renewed.expires_at > lease.expires_at
    with pytest.raises(ValueError):
        lease.renew(
            lease.reclaim_after,
            expires_at=lease.reclaim_after + timedelta(minutes=1),
            reclaim_after=lease.reclaim_after + timedelta(minutes=2),
        )


def test_reclaim_transitions_are_idempotent_and_retryable() -> None:
    lease = _lease()
    now = datetime.now(UTC)

    reclaiming = lease.begin_reclaim(now, reason="expired")
    failed = reclaiming.cleanup_failed(now + timedelta(seconds=1))

    assert reclaiming.state is LeaseState.RECLAIMING
    assert reclaiming.cleanup_attempts == 1
    assert reclaiming.begin_reclaim(now, reason="again") is reclaiming
    assert failed.is_reclaimable(now + timedelta(seconds=1))
    assert failed.begin_reclaim(now + timedelta(seconds=2), reason="retry").released(
        now
    ).state is LeaseState.RELEASED


def test_retries_back_off_within_one_shared_recovery_budget() -> None:
    policy = CleanupRetryPolicy(
        base_delay=timedelta(seconds=5),
        max_delay=timedelta(seconds=20),
        max_attempts=4,
        max_duration=timedelta(minutes=2),
    )
    now = datetime.now(UTC)
    first = _lease().begin_reclaim(now, reason="expired")
    second = first.cleanup_failed(now).begin_reclaim(
        now + timedelta(seconds=5), reason="retry"
    )

    assert second.reclaim_started_at == first.reclaim_started_at
    assert policy.retry_at(first, now=now) <= policy.retry_at(second, now=now)
    assert policy.retry_at(second, now=now) <= now + policy.max_delay
    assert not policy.is_exhausted(second, now=now)
    assert policy.is_exhausted(second, now=now + timedelta(minutes=3))
