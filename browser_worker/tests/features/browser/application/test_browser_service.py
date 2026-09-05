from uuid import uuid4

import pytest
from tests.fakes import FakeBrowserProcess

from browser_worker.features.browser.application.exceptions import (
    BrowserAlreadyRunningException,
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.service import BrowserService


@pytest.mark.asyncio
async def test_service_owns_browser_lifecycle() -> None:
    process = FakeBrowserProcess()
    service = BrowserService(process)

    browser_id = uuid4()

    created = await service.create(browser_id)
    repeated = await service.create(browser_id)

    assert repeated is created
    assert service.get() is created
    assert service.upstream_cdp_url(browser_id).endswith("/test")
    assert process.start_count == 1

    await service.destroy()
    assert process.stop_count == 1


@pytest.mark.asyncio
async def test_service_rejects_a_second_browser() -> None:
    service = BrowserService(FakeBrowserProcess())
    await service.create(uuid4())

    with pytest.raises(BrowserAlreadyRunningException):
        await service.create(uuid4())


@pytest.mark.asyncio
async def test_missing_browser_operations_fail_consistently() -> None:
    process = FakeBrowserProcess()
    service = BrowserService(process)

    with pytest.raises(BrowserNotFoundException):
        service.get()
    with pytest.raises(BrowserNotFoundException):
        service.upstream_cdp_url(uuid4())

    await service.destroy()
    assert process.stop_count == 0
