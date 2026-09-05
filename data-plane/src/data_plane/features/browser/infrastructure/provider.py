from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from data_plane.features.browser.application.ports import BrowserProcess
from data_plane.features.browser.application.service import BrowserService
from data_plane.features.browser.infrastructure.chrome_process import ChromeProcess
from data_plane.features.browser.infrastructure.settings import BrowserSettings


class BrowserProvider(Provider):
    def __init__(self, service: BrowserService | None = None) -> None:
        super().__init__()
        self._service = service

    @provide(scope=Scope.APP)
    def settings(self) -> BrowserSettings:
        return BrowserSettings()

    @provide(scope=Scope.APP)
    def browser_process(self, settings: BrowserSettings) -> BrowserProcess:
        return ChromeProcess(settings)

    @provide(scope=Scope.APP)
    async def browser_service(
        self,
        process: BrowserProcess,
    ) -> AsyncIterator[BrowserService]:
        service = self._service or BrowserService(process)
        try:
            yield service
        finally:
            await service.destroy()
