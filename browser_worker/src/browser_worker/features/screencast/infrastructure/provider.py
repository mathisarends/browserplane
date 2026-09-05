from dishka import Provider, Scope, provide

from browser_worker.features.browser.infrastructure.settings import BrowserSettings
from browser_worker.features.screencast.application.models import ScreencastOptions
from browser_worker.features.screencast.application.ports import FrameStreamFactory
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.screencast.infrastructure.settings import (
    ScreencastSettings,
)
from browser_worker.features.screencast.infrastructure.stream import CdpFrameStream


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
