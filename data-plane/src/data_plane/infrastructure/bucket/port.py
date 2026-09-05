from abc import ABC, abstractmethod

from data_plane.infrastructure.bucket.models import BucketObject


class Bucket(ABC):
    @abstractmethod
    async def put(self, item: BucketObject) -> None:
        """Persist an object under its key."""


class NullBucket(Bucket):
    async def put(self, item: BucketObject) -> None:
        return None
