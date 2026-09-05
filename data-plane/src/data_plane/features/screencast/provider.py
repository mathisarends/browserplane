from dishka import Provider, Scope, provide

from data_plane.features.screencast.application.models import ScreencastOptions
from data_plane.features.screencast.application.ports import FrameStreamFactory
from data_plane.features.screencast.application.service import ScreencastService
from data_plane.features.screencast.infrastructure.stream import CdpFrameStream
from data_plane.settings import DataPlaneSettings


class ScreencastProvider(Provider):
    @provide(scope=Scope.APP)
    def stream_factory(self, settings: DataPlaneSettings) -> FrameStreamFactory:
        options = ScreencastOptions(
            quality=settings.screencast_quality,
            width=settings.width,
            height=settings.height,
        )
        return lambda cdp_url: CdpFrameStream(cdp_url, options)

    @provide(scope=Scope.APP)
    def screencast_service(
        self, stream_factory: FrameStreamFactory
    ) -> ScreencastService:
        return ScreencastService(stream_factory)
