from abc import ABC, abstractmethod

from backend.infrastructure.bucket.models import BucketObject


class Bucket(ABC):
    @abstractmethod
    async def put(self, item: BucketObject) -> None:
        """Persist a streamed object under its key."""


class NullBucket(Bucket):
    async def put(self, item: BucketObject) -> None:
        async for _ in item.content:
            pass
