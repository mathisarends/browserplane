import pytest

from browser_worker.features.browser.application.exceptions import (
    BrowserStartupException,
)
from browser_worker.features.browser.infrastructure.chrome_process import ChromeProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings


def test_reports_an_explicitly_missing_browser() -> None:
    settings = BrowserSettings(
        _env_file=None,
        executable="browser-worker-test-missing-executable",
    )

    assert ChromeProcess(settings).is_available() is False


@pytest.mark.asyncio
async def test_start_rejects_an_explicitly_missing_browser() -> None:
    settings = BrowserSettings(
        _env_file=None,
        executable="browser-worker-test-missing-executable",
    )

    with pytest.raises(BrowserStartupException, match="No Chromium browser found"):
        await ChromeProcess(settings).start()
