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

    await service.create(7)
    await service.create(7)

    assert service.inspect().generation == 7
    assert service.upstream_cdp_url().endswith("/test")
    assert process.start_count == 1

    await service.release()
    assert process.stop_count == 1


@pytest.mark.asyncio
async def test_service_rejects_a_second_browser() -> None:
    service = BrowserService(FakeBrowserProcess())
    await service.create(7)

    with pytest.raises(BrowserAlreadyRunningException):
        await service.create(8)


@pytest.mark.asyncio
async def test_released_generation_cannot_be_started_again() -> None:
    service = BrowserService(FakeBrowserProcess())
    await service.create(7)

    assert await service.prepare_release(7)
    await service.stop_process()
    await service.finish_release(7, succeeded=True)

    with pytest.raises(BrowserAlreadyRunningException):
        await service.create(7)
    await service.create(8)
    assert service.inspect().generation == 8


@pytest.mark.asyncio
async def test_missing_browser_operations_fail_consistently() -> None:
    process = FakeBrowserProcess()
    service = BrowserService(process)

    with pytest.raises(BrowserNotFoundException):
        service.inspect()
    with pytest.raises(BrowserNotFoundException):
        service.upstream_cdp_url()

    await service.release()
    assert process.stop_count == 0
