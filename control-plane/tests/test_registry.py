from datetime import timedelta
from uuid import UUID

import pytest

from control_plane.registry import InMemoryBrowserStore
from control_plane.services import BrowserService, LeaseService
from control_plane.settings import BrowserSlot


class FakeProvisioner:
    async def provision(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot(UUID(int=1), "http://worker-1", "ws://tunnel-1/ws"),
            BrowserSlot(UUID(int=2), "http://worker-2", "ws://tunnel-2/ws"),
        )

    async def deprovision(self) -> None:
        pass


@pytest.mark.asyncio
async def test_browser_service_provisions_and_leases_a_browser() -> None:
    registry = InMemoryBrowserStore()
    browsers = BrowserService(FakeProvisioner(), registry)
    leases = LeaseService(registry)
    await browsers.start()

    lease = await leases.create(UUID(int=2), UUID(int=3), timedelta(minutes=1))

    assert browsers.get(UUID(int=2)).state == "leased"
    assert leases.get(lease.id) == lease

    await browsers.stop()
