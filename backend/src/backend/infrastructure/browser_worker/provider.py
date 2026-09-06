from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from httpx2 import AsyncClient

from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings


class BrowserWorkerProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> BrowserWorkerSettings:
        return BrowserWorkerSettings()

    @provide(scope=Scope.APP)
    async def client(
        self,
    ) -> AsyncIterator[AsyncClient]:
        async with AsyncClient() as http:
            yield http
