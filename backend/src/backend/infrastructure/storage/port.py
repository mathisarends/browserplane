from abc import ABC, abstractmethod

from backend.infrastructure.storage.models import StoredObject


class ObjectStorage(ABC):
    @abstractmethod
    async def put(self, item: StoredObject) -> None:
        """Persist a streamed object under its key."""


class NullObjectStorage(ObjectStorage):
    async def put(self, item: StoredObject) -> None:
        async for _ in item.content:
            pass
