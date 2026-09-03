from datetime import timedelta
from uuid import UUID

import pytest

from control_plane.features.browsers.application.models import BrowserSlot, BrowserState
from control_plane.features.browsers.application.ports import BrowserProvisioner
from control_plane.features.browsers.application.service import BrowserService
from control_plane.features.browsers.infrastructure.in_memory_registry import (
    InMemoryBrowserRegistry,
)
from control_plane.features.leases.application.service import LeaseService
from control_plane.features.leases.infrastructure.browser_service_allocator import (
    BrowserServiceAllocator,
)
from control_plane.features.leases.infrastructure.in_memory_store import (
    InMemoryLeaseStore,
)


class FakeProvisioner(BrowserProvisioner):
    async def provision(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot(UUID(int=1), "http://worker-1", "ws://tunnel-1/ws"),
            BrowserSlot(UUID(int=2), "http://worker-2", "ws://tunnel-2/ws"),
        )

    async def deprovision(self) -> None:
        pass


@pytest.mark.asyncio
async def test_browser_service_provisions_and_leases_a_browser() -> None:
    browsers = BrowserService(FakeProvisioner(), InMemoryBrowserRegistry())
    leases = LeaseService(BrowserServiceAllocator(browsers), InMemoryLeaseStore())
    await browsers.start()

    lease = await leases.create(UUID(int=2), UUID(int=3), timedelta(minutes=1))

    assert browsers.get(UUID(int=2)).state is BrowserState.LEASED
    assert await leases.get(lease.id) == lease

    await leases.release(lease.id)
    assert browsers.get(UUID(int=2)).state is BrowserState.READY

    await browsers.stop()
