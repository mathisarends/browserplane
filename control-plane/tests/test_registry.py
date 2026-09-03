import pytest

from control_plane.registry import BrowserNotFoundError, BrowserRegistry
from control_plane.settings import BrowserSlot


class FakeProvisioner:
    async def provision(self) -> tuple[BrowserSlot, BrowserSlot]:
        return (
            BrowserSlot("browser-1", "http://worker-1", "ws://tunnel-1/ws"),
            BrowserSlot("browser-2", "http://worker-2", "ws://tunnel-2/ws"),
        )

    async def deprovision(self) -> None:
        pass


@pytest.mark.asyncio
async def test_registry_provisions_two_browser_tunnels() -> None:
    registry = BrowserRegistry(FakeProvisioner())
    await registry.start()

    assert [browser.id for browser in registry.list()] == ["browser-1", "browser-2"]
    assert registry.get("browser-2").tunnel_url == "ws://tunnel-2/ws"

    await registry.stop()


@pytest.mark.asyncio
async def test_registry_rejects_unknown_browser() -> None:
    registry = BrowserRegistry(FakeProvisioner())
    await registry.start()

    with pytest.raises(BrowserNotFoundError):
        registry.get("browser-3")
