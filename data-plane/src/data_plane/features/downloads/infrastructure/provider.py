from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from data_plane.features.browser.application.service import BrowserService
from data_plane.features.downloads.application.service import DownloadService
from data_plane.features.workspace.application.workspace import Workspace


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
