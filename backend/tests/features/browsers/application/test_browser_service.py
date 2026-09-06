from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fakes.browser_provisioner import FakeBrowserProvisioner
from fakes.browser_repository import InMemoryBrowserRepository

from backend.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserProvisioningException,
    BrowserUnavailableException,
)
from backend.features.browsers.application.service import BrowserService
from backend.features.browsers.domain.models import Browser, BrowserSlot, BrowserState


def _browser(slot: BrowserSlot, *, state: BrowserState = BrowserState.READY) -> Browser:
    return Browser(slot=slot, created_at=datetime.now(UTC), state=state)


@pytest.mark.asyncio
async def test_start_registers_slots_and_preserves_existing_lifecycle() -> None:
    first = BrowserSlot(uuid4(), "http://worker-one")
    second = BrowserSlot(uuid4(), "http://worker-two")
    repository = InMemoryBrowserRepository()
    await repository.save(
        browser=Browser(
            slot=first,
            created_at=datetime.now(UTC) - timedelta(days=1),
            state=BrowserState.LEASED,
            generation=4,
        )
    )
    service = BrowserService(FakeBrowserProvisioner((first, second)), repository)

    await service.start()

    restored, added = await service.list()
    assert restored.slot == first
    assert restored.state is BrowserState.LEASED
    assert restored.generation == 4
    assert added.slot == second
    assert added.state is BrowserState.STOPPED


@pytest.mark.asyncio
async def test_pool_operations_keep_availability_and_generations_consistent() -> None:
    slot = BrowserSlot(uuid4(), "http://worker")
    provisioner = FakeBrowserProvisioner()
    repository = InMemoryBrowserRepository()
    browser = await repository.save(browser=_browser(slot))
    service = BrowserService(provisioner, repository)

    assert await service.remaining_capacity() == 1
    assert await service.reserve(browser.id) == 0
    assert (await service.get(browser.id)).state is BrowserState.LEASED

    with pytest.raises(BrowserUnavailableException):
        await service.reserve(browser.id)
    with pytest.raises(BrowserCapacityExhaustedException):
        await service.create()

    released = await service.release(browser.id)
    assert released.state is BrowserState.STOPPED
    assert released.generation == 1
    assert provisioner.released == [(slot, 0)]

    restarted = await service.restart(browser.id)
    assert restarted.state is BrowserState.READY
    assert restarted.generation == 2
    assert provisioner.released == [(slot, 0), (slot, 1)]
    assert provisioner.started == [(slot, 2)]


@pytest.mark.asyncio
async def test_recycle_ignores_unassigned_slots_and_cleans_leased_ones() -> None:
    ready_slot = BrowserSlot(uuid4(), "http://ready-worker")
    leased_slot = BrowserSlot(uuid4(), "http://leased-worker")
    provisioner = FakeBrowserProvisioner()
    repository = InMemoryBrowserRepository()
    ready = await repository.save(browser=_browser(ready_slot))
    leased = await repository.save(
        browser=_browser(leased_slot, state=BrowserState.LEASED)
    )
    service = BrowserService(provisioner, repository)

    await service.recycle(ready.id)
    await service.recycle(leased.id)
    await service.recycle(uuid4())

    assert provisioner.released == [(leased_slot, 0)]
    cleaned = await service.get(leased.id)
    assert cleaned.state is BrowserState.STOPPED
    assert cleaned.generation == 1


@pytest.mark.asyncio
async def test_worker_failures_are_translated_and_mark_recycling_failed() -> None:
    slot = BrowserSlot(uuid4(), "http://worker")
    provisioner = FakeBrowserProvisioner()
    repository = InMemoryBrowserRepository()
    browser = await repository.save(
        browser=_browser(slot, state=BrowserState.LEASED)
    )
    service = BrowserService(provisioner, repository)
    provisioner.release_error = RuntimeError("worker unavailable")

    with pytest.raises(BrowserProvisioningException):
        await service.recycle(browser.id)

    assert (await service.get(browser.id)).state is BrowserState.FAILED
    with pytest.raises(BrowserNotFoundException):
        await service.get(uuid4())
