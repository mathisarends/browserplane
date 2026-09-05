import asyncio

import pytest

from browser_worker.features.browser.infrastructure.chrome_process import ChromeProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings
from browser_worker.features.screencast.application.models import ScreencastOptions
from browser_worker.features.screencast.infrastructure.stream import CdpFrameStream


@pytest.mark.asyncio
async def test_running_browser_produces_a_jpeg_screencast_frame() -> None:
    settings = BrowserSettings(
        _env_file=None,
        headless=True,
        width=320,
        height=240,
        startup_timeout=10,
    )
    if not ChromeProcess.is_available(settings):
        pytest.skip("Chromium is not available")

    browser = ChromeProcess(settings)
    cdp_url = await browser.start()
    stream = CdpFrameStream(
        cdp_url,
        ScreencastOptions(quality=50, width=320, height=240),
    )

    try:
        async with stream.subscribe() as frames:
            frame = await asyncio.wait_for(anext(frames), timeout=10)
    finally:
        await browser.stop()

    assert frame.startswith(b"\xff\xd8")
    assert frame.endswith(b"\xff\xd9")
