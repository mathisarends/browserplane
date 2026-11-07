from dishka import Provider, Scope, provide

from backend.infrastructure.storage.credentials import StorageCredentials
from backend.infrastructure.storage.port import NullObjectStorage, ObjectStorage
from backend.infrastructure.storage.s3 import S3ObjectStorage
from backend.infrastructure.storage.settings import StorageSettings


class StorageProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> StorageSettings:
        return StorageSettings()

    @provide(scope=Scope.APP)
    def credentials(
        self,
        # smelt: ignore[SMT328] -- Environment options, not DI.
    ) -> StorageCredentials:
        return StorageCredentials()

    @provide(scope=Scope.APP)
    def storage(
        self, settings: StorageSettings, credentials: StorageCredentials
    ) -> ObjectStorage:
        if settings.bucket is None:
            return NullObjectStorage()
        return S3ObjectStorage(settings, credentials)
