from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from browser_worker.features.browser.application import BrowserEndpoint, BrowserService
from browser_worker.features.browser.domain import BrowserProcess
from browser_worker.features.browser.infrastructure.chrome_process import ChromeProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings


class BrowserProvider(Provider):
    def __init__(self, service: BrowserService | None = None) -> None:
        super().__init__()
        self._service = service

    @provide(scope=Scope.APP)
    def endpoint(self, settings: BrowserSettings) -> BrowserEndpoint:
        return BrowserEndpoint(settings.public_base_url)

    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> BrowserSettings:
        return BrowserSettings()

    browser_process = provide(ChromeProcess, scope=Scope.APP, provides=BrowserProcess)

    @provide(scope=Scope.APP)
    async def browser_service(
        self,
        process: BrowserProcess,
    ) -> AsyncIterator[BrowserService]:
        service = self._service or BrowserService(process)
        try:
            yield service
        finally:
            await service.release()
