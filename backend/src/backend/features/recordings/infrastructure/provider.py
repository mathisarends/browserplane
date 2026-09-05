from dishka import Provider, Scope, provide

from backend.features.browsers.application.service import BrowserService
from backend.features.recordings.application.ports import RecordingGateway
from backend.features.recordings.application.service import RecordingService
from backend.features.recordings.infrastructure.browser_worker_gateway import (
    BrowserWorkerRecordingGateway,
)
from backend.infrastructure.bucket import Bucket


class RecordingProvider(Provider):
    def __init__(self, gateway: RecordingGateway | None = None) -> None:
        super().__init__()
        self._gateway = gateway

    @provide(scope=Scope.APP, provides=RecordingGateway)
    def gateway(self, bucket: Bucket) -> RecordingGateway:
        return self._gateway or BrowserWorkerRecordingGateway(bucket)

    @provide(scope=Scope.REQUEST)
    def service(
        self, browsers: BrowserService, gateway: RecordingGateway
    ) -> RecordingService:
        return RecordingService(browsers, gateway)
