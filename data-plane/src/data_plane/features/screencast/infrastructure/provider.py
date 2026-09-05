from dishka import Provider, Scope, provide

from data_plane.features.browser.infrastructure.settings import BrowserSettings
from data_plane.features.screencast.application.models import ScreencastOptions
from data_plane.features.screencast.application.ports import FrameStreamFactory
from data_plane.features.screencast.application.service import ScreencastService
from data_plane.features.screencast.infrastructure.settings import ScreencastSettings
from data_plane.features.screencast.infrastructure.stream import CdpFrameStream


class ScreencastProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> ScreencastSettings:
        return ScreencastSettings()

    @provide(scope=Scope.APP)
    def stream_factory(
        self,
        settings: ScreencastSettings,
        browser_settings: BrowserSettings,
    ) -> FrameStreamFactory:
        options = ScreencastOptions(
            quality=settings.quality,
            width=browser_settings.width,
            height=browser_settings.height,
        )
        return lambda cdp_url: CdpFrameStream(cdp_url, options)

    @provide(scope=Scope.APP)
    def screencast_service(
        self, stream_factory: FrameStreamFactory
    ) -> ScreencastService:
        return ScreencastService(stream_factory)
