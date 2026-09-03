import pytest

from data_plane.application.models import BrowserState
from data_plane.application.ports import BrowserProcess
from data_plane.application.service import BrowserService
from data_plane.settings import DataPlaneSettings


class FakeProcess(BrowserProcess):
    stopped = False

    async def start(self) -> str:
        return "ws://chromium/devtools/browser/test"

    async def stop(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_service_owns_browser_lifecycle() -> None:
    process = FakeProcess()
    service = BrowserService(
        DataPlaneSettings(public_base_url="ws://worker:8000", _env_file=None),
        process_factory=lambda _: process,
    )

    browser = await service.create("browser-1")

    assert browser.cdp_url == "ws://worker:8000/api/v1/browsers/browser-1/cdp"
    assert service.get("browser-1").state is BrowserState.READY
    assert service.capacity().available == 0

    await service.destroy("browser-1")
    assert process.stopped is True
    assert service.capacity().available == 1
