from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from browser_worker.features.browser.application import BrowserService
from browser_worker.features.downloads.application import DownloadService, DownloadStore
from browser_worker.features.downloads.infrastructure.cdp import CdpDownloadStore


class DownloadProvider(Provider):
    download_store = provide(CdpDownloadStore, scope=Scope.APP, provides=DownloadStore)

    @provide(scope=Scope.APP)
    async def download_service(
        self, browsers: BrowserService, store: DownloadStore
    ) -> AsyncIterator[DownloadService]:
        service = DownloadService(browsers, store)
        try:
            yield service
        finally:
            await service.stop()
