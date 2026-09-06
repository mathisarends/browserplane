import asyncio
import http.server
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.browser.infrastructure.chrome_process import ChromeProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.state.application.models import (
    BrowserState,
    BrowserTabState,
)
from browser_worker.features.state.infrastructure.cdp import (
    CdpBrowserStateStore,
)
from browser_worker.features.state.infrastructure.settings import (
    BrowserStateSettings,
)
from browser_worker.features.workspace.application.workspace import Workspace


class DownloadHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/artifact.txt":
            body = b"downloaded through Chromium\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header(
                "Content-Disposition", 'attachment; filename="artifact.txt"'
            )
        else:
            body = (
                b'<!doctype html><a id="download" href="/artifact.txt" download>'
                b"download</a><script>download.click()</script>"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        pass


@contextmanager
def serve_download() -> Generator[str]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DownloadHandler)
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
async def test_download_service_collects_and_clears_a_chromium_download(
    tmp_path: Path,
) -> None:
    settings = BrowserSettings(
        _env_file=None,
        headless=True,
        width=320,
        height=240,
        startup_timeout=10,
    )
    if not ChromeProcess(settings).is_available():
        pytest.skip("Chromium is not available")

    browsers = BrowserService(ChromeProcess(settings))
    browser_id = await browsers.create(uuid4())
    downloads = DownloadService(browsers, Workspace(tmp_path / "workspace"))
    await downloads.start(browser_id)

    try:
        with serve_download() as origin:
            state = CdpBrowserStateStore(
                browsers.upstream_cdp_url(browser_id),
                BrowserStateSettings(_env_file=None, restore_timeout=5),
            )
            await state.restore_browser(
                BrowserState(tabs=(BrowserTabState(url=f"{origin}/"),))
            )

            async with asyncio.timeout(10):
                while not downloads.list(browser_id):
                    await asyncio.sleep(0.05)

            (download,) = downloads.list(browser_id)
            assert download.filename == "artifact.txt"
            assert downloads.file(browser_id, download.id).path.read_bytes() == (
                b"downloaded through Chromium\n"
            )

            await downloads.clear(browser_id)
            assert downloads.list(browser_id) == ()
            assert not download.path.exists()
    finally:
        await downloads.stop()
        await browsers.release()
