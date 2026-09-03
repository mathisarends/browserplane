import pytest

from data_plane.manager import BrowserManager
from data_plane.settings import DataPlaneSettings


class FakeProcess:
    stopped = False

    async def start(self) -> str:
        return "ws://chromium/devtools/browser/test"

    async def stop(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_manager_owns_browser_lifecycle() -> None:
    process = FakeProcess()
    manager = BrowserManager(
        DataPlaneSettings(public_base_url="ws://worker:8000", _env_file=None),
        process_factory=lambda _: process,
    )

    browser = await manager.create("browser-1")

    assert browser.cdp_url == "ws://worker:8000/api/browsers/browser-1/cdp"
    assert manager.inspect("browser-1").state == "ready"
    assert manager.capacity() == (1, 0)

    await manager.destroy("browser-1")
    assert process.stopped is True
    assert manager.capacity() == (1, 1)
