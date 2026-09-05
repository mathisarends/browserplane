from dishka import Provider, Scope, provide

from data_plane.infrastructure.bucket.credentials import BucketCredentials
from data_plane.infrastructure.bucket.port import Bucket, NullBucket
from data_plane.infrastructure.bucket.s3 import S3Bucket
from data_plane.infrastructure.bucket.settings import BucketSettings
from data_plane.settings import DataPlaneSettings


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> DataPlaneSettings:
        return DataPlaneSettings()

    @provide(scope=Scope.APP)
    def bucket_settings(self) -> BucketSettings:
        return BucketSettings()

    @provide(scope=Scope.APP)
    def bucket_credentials(self) -> BucketCredentials:
        return BucketCredentials()

    @provide(scope=Scope.APP)
    def bucket(
        self, settings: BucketSettings, credentials: BucketCredentials
    ) -> Bucket:
        if settings.name is None:
            return NullBucket()
        return S3Bucket(settings, credentials)
