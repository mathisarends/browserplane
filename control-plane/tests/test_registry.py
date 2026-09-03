import pytest

from control_plane.provisioning import ComposeBrowserProvisioner
from control_plane.registry import BrowserNotFoundError, BrowserRegistry
from control_plane.settings import ControlPlaneSettings


@pytest.mark.asyncio
async def test_registry_provisions_two_browser_tunnels() -> None:
    registry = BrowserRegistry(ComposeBrowserProvisioner(ControlPlaneSettings()))
    await registry.start()

    assert [browser.id for browser in registry.list()] == ["browser-1", "browser-2"]
    assert registry.get("browser-2").tunnel_url.endswith(":8002/api/browser/ws")

    await registry.stop()


@pytest.mark.asyncio
async def test_registry_rejects_unknown_browser() -> None:
    registry = BrowserRegistry(ComposeBrowserProvisioner(ControlPlaneSettings()))
    await registry.start()

    with pytest.raises(BrowserNotFoundError):
        registry.get("browser-3")
