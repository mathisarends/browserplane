from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from data_plane.features.browser.application.service import BrowserService
from data_plane.features.recordings.application.ports import ScreenRecorder
from data_plane.features.recordings.application.service import (
    RecorderFactory,
    RecordingService,
)
from data_plane.features.recordings.infrastructure.ffmpeg_recorder import (
    FfmpegScreenRecorder,
)
from data_plane.features.recordings.infrastructure.settings import RecordingSettings
from data_plane.features.screencast.application.service import ScreencastService
from data_plane.features.workspace.application.workspace import Workspace


class RecordingProvider(Provider):
    def __init__(self, service: RecordingService | None = None) -> None:
        super().__init__()
        self._service = service

    @provide(scope=Scope.APP)
    def settings(self) -> RecordingSettings:
        return RecordingSettings()

    @provide(scope=Scope.APP)
    def recorder_factory(
        self,
        screencasts: ScreencastService,
        settings: RecordingSettings,
    ) -> RecorderFactory:
        def build(cdp_url: str) -> ScreenRecorder:
            return FfmpegScreenRecorder(screencasts.for_browser(cdp_url), settings)

        return build

    @provide(scope=Scope.APP)
    async def recording_service(
        self,
        browsers: BrowserService,
        workspace: Workspace,
        recorder_factory: RecorderFactory,
    ) -> AsyncIterator[RecordingService]:
        service = self._service or RecordingService(
            browsers, workspace, recorder_factory
        )
        try:
            yield service
        finally:
            await service.destroy()
