from dishka import Provider, Scope, provide

from backend.infrastructure.bucket.credentials import BucketCredentials
from backend.infrastructure.bucket.port import Bucket, NullBucket
from backend.infrastructure.bucket.s3 import S3Bucket
from backend.infrastructure.bucket.settings import BucketSettings


class BucketProvider(Provider):
    @provide(scope=Scope.APP)
    def settings(self) -> BucketSettings:
        return BucketSettings()

    @provide(scope=Scope.APP)
    def credentials(self) -> BucketCredentials:
        return BucketCredentials()

    @provide(scope=Scope.APP)
    def bucket(
        self, settings: BucketSettings, credentials: BucketCredentials
    ) -> Bucket:
        if settings.name is None:
            return NullBucket()
        return S3Bucket(settings, credentials)
