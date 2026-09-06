import functools
import http.server
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import pytest

from browser_worker.features.browser.infrastructure.chrome_process import ChromeProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings
from browser_worker.features.state.application.models import (
    AuthenticationState,
    BrowserState,
    BrowserTabState,
    OriginLocalStorage,
    StorageItem,
)
from browser_worker.features.state.infrastructure.cdp import (
    CdpBrowserStateStore,
)
from browser_worker.features.state.infrastructure.settings import (
    BrowserStateSettings,
)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def serve(directory: Path) -> Generator[str]:
    handler = functools.partial(QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.asyncio
async def test_browser_state_roundtrips_through_real_chromium(tmp_path: Path) -> None:
    browser_settings = BrowserSettings(
        _env_file=None,
        headless=True,
        width=320,
        height=240,
        startup_timeout=10,
    )
    if not ChromeProcess(browser_settings).is_available():
        pytest.skip("Chromium is not available")

    (tmp_path / "index.html").write_text(
        "<!doctype html><title>state test</title><main>ready</main>",
        encoding="utf-8",
    )

    with serve(tmp_path) as origin:
        browser = ChromeProcess(browser_settings)
        cdp_url = await browser.start()
        store = CdpBrowserStateStore(
            cdp_url,
            BrowserStateSettings(_env_file=None, restore_timeout=5),
        )
        authentication = AuthenticationState(
            local_storage=(
                OriginLocalStorage(
                    origin=origin,
                    local_storage=(StorageItem("token", "secret"),),
                ),
            )
        )
        state = BrowserState(
            tabs=(
                BrowserTabState(
                    url=f"{origin}/index.html",
                    session_storage=(StorageItem("draft", "hello"),),
                ),
            )
        )

        try:
            await store.restore_authentication(authentication)
            await store.restore_browser(state)

            captured_authentication = await store.capture_authentication((origin,))
            captured_state = await store.capture_browser()
        finally:
            await browser.stop()

    assert captured_authentication.local_storage == authentication.local_storage
    assert len(captured_state.tabs) == 1
    assert captured_state.tabs[0].url == state.tabs[0].url
    assert captured_state.tabs[0].session_storage == state.tabs[0].session_storage
