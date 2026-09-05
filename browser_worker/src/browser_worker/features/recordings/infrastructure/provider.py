from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.application.service import (
    RecorderFactory,
    RecordingService,
)
from browser_worker.features.recordings.infrastructure.ffmpeg_recorder import (
    FfmpegScreenRecorder,
)
from browser_worker.features.recordings.infrastructure.settings import RecordingSettings
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.workspace.application.workspace import Workspace


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
