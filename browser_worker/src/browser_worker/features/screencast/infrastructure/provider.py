from dishka import Provider, Scope, provide

from browser_worker.features.screencast.application.ports import FrameStreamFactory
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
    ScreencastOptions,
)
from browser_worker.features.screencast.infrastructure.stream import CdpFrameStream


class ScreencastProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ScreencastOptions:
        return ScreencastOptions()

    @provide(scope=Scope.APP)
    def dirty_rectangle_settings(self) -> DirtyRectangleSettings:
        return DirtyRectangleSettings()

    @provide(scope=Scope.APP)
    def stream_factory(
        self,
        settings: ScreencastOptions,
    ) -> FrameStreamFactory:
        return lambda cdp_url: CdpFrameStream(cdp_url, settings)

    @provide(scope=Scope.APP)
    def screencast_service(
        self, stream_factory: FrameStreamFactory
    ) -> ScreencastService:
        return ScreencastService(stream_factory)
