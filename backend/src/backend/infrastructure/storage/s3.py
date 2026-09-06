from typing import TYPE_CHECKING

import obstore
from obstore.store import S3Store

from backend.infrastructure.storage.credentials import StorageCredentials
from backend.infrastructure.storage.models import StoredObject
from backend.infrastructure.storage.port import ObjectStorage
from backend.infrastructure.storage.settings import StorageSettings

if TYPE_CHECKING:
    from obstore import Attributes
    from obstore.store import S3Config


class S3ObjectStorage(ObjectStorage):
    """Relay async HTTP chunks into an S3-compatible store.

    obstore streams the body and switches to a multipart upload on its own, so
    the object never has to be buffered here in full.
    """

    def __init__(
        self, settings: StorageSettings, credentials: StorageCredentials
    ) -> None:
        if settings.bucket is None:
            raise ValueError("A bucket name is required")
        self._store = S3Store(
            settings.bucket,
            prefix=settings.prefix or None,
            config=_config(settings, credentials),
            client_options={"allow_http": True},
        )

    async def put(self, item: StoredObject) -> None:
        await obstore.put_async(
            self._store,
            item.key,
            item.content,
            attributes=_attributes(item.content_type),
        )


def _config(settings: StorageSettings, credentials: StorageCredentials) -> S3Config:
    config: S3Config = {"region": settings.region}
    if settings.endpoint is not None:
        config["endpoint"] = settings.endpoint
    if credentials.access_key is not None:
        config["access_key_id"] = credentials.access_key
    if credentials.secret_key is not None:
        config["secret_access_key"] = credentials.secret_key
    return config


def _attributes(content_type: str | None) -> Attributes | None:
    return {"Content-Type": content_type} if content_type else None
