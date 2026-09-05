from uuid import uuid4

import pytest

from data_plane.features.browser.application.ports import BrowserProcess
from data_plane.features.browser.application.service import BrowserService


class FakeProcess(BrowserProcess):
    stopped = False

    async def start(self) -> str:
        return "ws://chromium/devtools/browser/test"

    async def stop(self) -> None:
        self.stopped = True


@pytest.mark.asyncio
async def test_service_owns_browser_lifecycle() -> None:
    process = FakeProcess()
    service = BrowserService(process)

    browser_id = uuid4()

    await service.create(browser_id)

    assert service.get().id == browser_id

    await service.destroy()
    assert process.stopped is True
