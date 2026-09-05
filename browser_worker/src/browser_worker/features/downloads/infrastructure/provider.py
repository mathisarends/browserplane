from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.workspace.application.workspace import Workspace


class DownloadProvider(Provider):
    @provide(scope=Scope.APP)
    async def download_service(
        self, browsers: BrowserService, workspace: Workspace
    ) -> AsyncIterator[DownloadService]:
        service = DownloadService(browsers, workspace)
        try:
            yield service
        finally:
            await service.stop()
