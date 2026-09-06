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
    allocator: FakeBrowserAllocator, store: InMemoryLeaseStore
) -> LeaseService:
    return LeaseService(
        allocator,
        store,
        LeaseSettings(
            ttl_seconds=30,
            grace_period_seconds=10,
            cleanup_retry_seconds=1,
            _env_file=None,
        ),
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
