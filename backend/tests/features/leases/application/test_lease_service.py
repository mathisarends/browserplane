from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fakes.browser_allocator import FakeBrowserAllocator
from fakes.lease_store import InMemoryLeaseStore

from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.service import LeaseService
from backend.features.leases.domain.models import Lease, LeaseState
from backend.features.leases.settings import LeaseSettings


def _service(
    allocator: FakeBrowserAllocator,
    store: InMemoryLeaseStore,
    *,
    cleanup_max_attempts: int = 5,
) -> LeaseService:
    return LeaseService(
        allocator,
        store,
        LeaseSettings(
            ttl_seconds=30,
            grace_period_seconds=10,
            cleanup_retry_seconds=1,
            cleanup_max_attempts=cleanup_max_attempts,
            _env_file=None,
        ),
    )


def _due_lease() -> Lease:
    now = datetime.now(UTC)
    return Lease(
        id=uuid4(),
        browser_id=uuid4(),
        owner_id=uuid4(),
        generation=2,
        state=LeaseState.ACTIVE,
        created_at=now - timedelta(minutes=2),
        last_renewed_at=now - timedelta(minutes=2),
        expires_at=now - timedelta(minutes=1),
        reclaim_after=now - timedelta(seconds=1),
    )


@pytest.mark.asyncio
async def test_lease_lifecycle_reserves_renews_and_releases_a_browser() -> None:
    allocator = FakeBrowserAllocator(generation=7)
    store = InMemoryLeaseStore()
    service = _service(allocator, store)
    browser_id = uuid4()
    owner_id = uuid4()

    lease = await service.create(browser_id, owner_id)
    renewed = await service.renew(lease.id)
    await service.release(lease.id)
    await service.release(lease.id)

    assert allocator.reserved == [browser_id]
    assert renewed.generation == 7
    assert renewed.expires_at >= lease.expires_at
    assert allocator.recycled == [browser_id]
    assert await service.list() == ()
    with pytest.raises(LeaseNotFoundException):
        await service.get(lease.id)


@pytest.mark.asyncio
async def test_inspection_preserves_history_but_active_access_rejects_expired_lease(
) -> None:
    allocator = FakeBrowserAllocator()
    store = InMemoryLeaseStore()
    service = _service(allocator, store)
    now = datetime.now(UTC)
    expired = Lease(
        id=uuid4(),
        browser_id=uuid4(),
        owner_id=uuid4(),
        generation=0,
        state=LeaseState.ACTIVE,
        created_at=now - timedelta(minutes=2),
        last_renewed_at=now - timedelta(minutes=2),
        expires_at=now - timedelta(seconds=1),
        reclaim_after=now + timedelta(minutes=1),
    )
    await store.save(expired)

    assert await service.inspect(expired.id) == expired
    with pytest.raises(LeaseNotFoundException):
        await service.get(expired.id)
    with pytest.raises(LeaseNotFoundException):
        await service.renew(uuid4())


@pytest.mark.asyncio
async def test_reaper_retries_failed_cleanup_then_releases_it() -> None:
    allocator = FakeBrowserAllocator()
    store = InMemoryLeaseStore()
    service = _service(allocator, store)
    now = datetime.now(UTC)
    lease = Lease(
        id=uuid4(),
        browser_id=uuid4(),
        owner_id=uuid4(),
        generation=2,
        state=LeaseState.ACTIVE,
        created_at=now - timedelta(minutes=2),
        last_renewed_at=now - timedelta(minutes=2),
        expires_at=now - timedelta(minutes=1),
        reclaim_after=now - timedelta(seconds=1),
    )
    await store.save(lease)
    allocator.recycle_error = RuntimeError("worker unavailable")

    assert await service.reap_due() == ()
    failed = await store.get(lease.id)
    assert failed is not None
    assert failed.state is LeaseState.FAILED
    assert failed.cleanup_attempts == 1

    allocator.recycle_error = None
    await store.save(failed.cleanup_failed(datetime.now(UTC) - timedelta(seconds=1)))
    assert await service.reap_due() == (lease.id,)
    assert allocator.recycled == [lease.browser_id, lease.browser_id]
    assert (await store.get(lease.id)).state is LeaseState.RELEASED


@pytest.mark.asyncio
async def test_cleanup_that_stays_broken_replaces_the_worker() -> None:
    allocator = FakeBrowserAllocator()
    store = InMemoryLeaseStore()
    service = _service(allocator, store, cleanup_max_attempts=2)
    lease = _due_lease()
    await store.save(lease)
    allocator.recycle_error = RuntimeError("worker will not clean up")

    assert await service.reap_due() == ()
    backed_off = await store.get(lease.id)
    assert backed_off is not None
    assert backed_off.state is LeaseState.FAILED
    assert backed_off.cleanup_retry_at is not None

    due_again = backed_off.cleanup_failed(datetime.now(UTC) - timedelta(seconds=1))
    await store.save(due_again)

    assert await service.reap_due() == (lease.id,)
    assert allocator.replaced == [lease.browser_id]
    released = await store.get(lease.id)
    assert released is not None
    assert released.state is LeaseState.RELEASED


@pytest.mark.asyncio
async def test_a_worker_that_cannot_be_replaced_quarantines_its_lease() -> None:
    allocator = FakeBrowserAllocator()
    store = InMemoryLeaseStore()
    service = _service(allocator, store, cleanup_max_attempts=1)
    lease = _due_lease()
    await store.save(lease)
    allocator.recycle_error = RuntimeError("worker will not clean up")
    allocator.replace_error = RuntimeError("worker will not come back")

    assert await service.reap_due() == ()
    quarantined = await store.get(lease.id)
    assert quarantined is not None
    assert quarantined.state is LeaseState.QUARANTINED

    # Quarantine ends the retry loop instead of feeding it forever.
    assert await service.reap_due() == ()
    assert allocator.replaced == [lease.browser_id]
