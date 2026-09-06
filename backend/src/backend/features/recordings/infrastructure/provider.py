from dishka import Provider, Scope, provide
from httpx2 import AsyncClient

from backend.features.browsers.application.service import BrowserService
from backend.features.recordings.application.ports import Recorder
from backend.features.recordings.application.service import RecordingService
from backend.features.recordings.infrastructure.browser_worker import (
    BrowserWorkerRecorder,
)
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from backend.infrastructure.bucket import Bucket


class RecordingProvider(Provider):
    def __init__(self, recorder: Recorder | None = None) -> None:
        super().__init__()
        self._recorder = recorder

    @provide(scope=Scope.APP, provides=Recorder)
    def recorder(
        self,
        bucket: Bucket,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
    ) -> Recorder:
        return self._recorder or BrowserWorkerRecorder(bucket, http, settings)

    @provide(scope=Scope.REQUEST)
    def service(self, browsers: BrowserService, recorder: Recorder) -> RecordingService:
        return RecordingService(browsers, recorder)
