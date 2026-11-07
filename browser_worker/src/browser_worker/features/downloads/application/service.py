from browser_worker.features.browser.application import BrowserService
from browser_worker.features.downloads.application.models import Download
from browser_worker.features.downloads.application.ports import DownloadStore


class DownloadService:
    def __init__(self, browsers: BrowserService, store: DownloadStore) -> None:
        self._browsers = browsers
        self._store = store

    async def start(self) -> None:
        browser = self._browsers.inspect()
        await self._store.start(browser.upstream_cdp_url)

    def list(self) -> tuple[Download, ...]:
        self._browsers.inspect()
        downloads = self._store.list()
        return downloads

    def file(self, download_id: str) -> Download:
        self._browsers.inspect()
        download = self._store.file(download_id)
        return download

    async def clear(self) -> None:
        self._browsers.inspect()
        await self._store.clear()

    async def stop(self) -> None:
        await self._store.stop()

    @property
    def is_idle(self) -> bool:
        return self._store.is_idle
