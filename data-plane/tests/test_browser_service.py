from uuid import uuid4

import pytest

from data_plane.features.browsers.application.ports import BrowserProcess
from data_plane.features.browsers.application.service import BrowserService
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

    browser_id = uuid4()

    browser = await service.create(browser_id)

    assert browser.cdp_url == f"ws://worker:8000/api/v1/browsers/{browser_id}/cdp"
    assert service.get(browser_id).id == browser_id
    assert service.capacity().available == 0

    await service.destroy(browser_id)
    assert process.stopped is True
    assert service.capacity().available == 1
