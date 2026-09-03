from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from data_plane.application.service import BrowserService
from data_plane.infrastructure.chrome_process import ChromeProcess
from data_plane.settings import DataPlaneSettings


class DataPlaneProvider(Provider):
    def __init__(self, service: BrowserService | None = None) -> None:
        super().__init__()
        self._service = service

    @provide(scope=Scope.APP)
    def settings(self) -> DataPlaneSettings:
        return DataPlaneSettings()

    @provide(scope=Scope.APP)
    async def browser_service(
        self, settings: DataPlaneSettings
    ) -> AsyncIterator[BrowserService]:
        service = self._service or BrowserService(settings, ChromeProcess)
        try:
            yield service
        finally:
            await service.close()
