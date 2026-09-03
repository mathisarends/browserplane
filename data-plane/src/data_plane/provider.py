from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from data_plane.manager import BrowserManager
from data_plane.settings import DataPlaneSettings


class DataPlaneProvider(Provider):
    def __init__(self, manager: BrowserManager | None = None) -> None:
        super().__init__()
        self._manager = manager

    @provide(scope=Scope.APP)
    def settings(self) -> DataPlaneSettings:
        return DataPlaneSettings()

    @provide(scope=Scope.APP)
    async def manager(
        self, settings: DataPlaneSettings
    ) -> AsyncIterator[BrowserManager]:
        manager = self._manager or BrowserManager(settings)
        try:
            yield manager
        finally:
            await manager.close()
