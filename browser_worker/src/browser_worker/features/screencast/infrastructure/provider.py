from dishka import Provider, Scope, provide

from browser_worker.features.screencast.application import (
    FramePackager,
    ScreencastMode,
    ScreencastService,
)
from browser_worker.features.screencast.domain import FrameStream, FrameStreamFactory
from browser_worker.features.screencast.infrastructure.dirty_rectangles import (
    DirtyRectangleJpegStream,
)
from browser_worker.features.screencast.infrastructure.fmp4 import Fmp4FrameStream
from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
    ScreencastOptions,
)
from browser_worker.features.screencast.infrastructure.stream import CdpFrameStream


class ScreencastProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> ScreencastOptions:
        return ScreencastOptions()

    @provide(scope=Scope.APP)
    def dirty_rectangle_settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> DirtyRectangleSettings:
        return DirtyRectangleSettings()

    @provide(scope=Scope.APP)
    def packager(self, settings: DirtyRectangleSettings) -> FramePackager:
        return lambda frames, mode: _package_frames(
            frames, mode=mode, settings=settings
        )

    @provide(scope=Scope.APP)
    def stream_factory(
        self,
        settings: ScreencastOptions,
    ) -> FrameStreamFactory:
        return lambda cdp_url: CdpFrameStream(cdp_url, settings)

    screencast_service = provide(
        ScreencastService, scope=Scope.APP, provides=ScreencastService
    )


def _package_frames(
    frames: FrameStream, *, mode: ScreencastMode, settings: DirtyRectangleSettings
) -> FrameStream:
    match mode:
        case ScreencastMode.JPEG:
            return frames
        case ScreencastMode.DIRTY_RECTANGLES:
            return DirtyRectangleJpegStream(frames, settings)
        case ScreencastMode.FMP4:
            return Fmp4FrameStream(frames)
