from typing import Any

from pydantic import Field

from browser_worker.features.state.application.models import (
    AuthenticationState,
    BrowserCookie,
    BrowserState,
    BrowserTabState,
    CookiePartitionKey,
    IndexedDbDatabase,
    IndexedDbIndex,
    IndexedDbObjectStore,
    IndexedDbRecord,
    OriginIndexedDb,
    OriginLocalStorage,
    ScrollPosition,
    StorageItem,
)


class StorageItemSchema(StorageItem):
    pass


class OriginLocalStorageSchema(OriginLocalStorage):
    local_storage: tuple[StorageItemSchema, ...] = Field(
        default=(), alias="localStorage"
    )


class IndexedDbIndexSchema(IndexedDbIndex):
    key_path: str | tuple[str, ...] | None = Field(default=None, alias="keyPath")


class IndexedDbRecordSchema(IndexedDbRecord):
    key: Any
    value: Any


class IndexedDbObjectStoreSchema(IndexedDbObjectStore):
    key_path: str | tuple[str, ...] | None = Field(default=None, alias="keyPath")
    indexes: tuple[IndexedDbIndexSchema, ...] = ()
    records: tuple[IndexedDbRecordSchema, ...] = ()


class IndexedDbDatabaseSchema(IndexedDbDatabase):
    object_stores: tuple[IndexedDbObjectStoreSchema, ...] = Field(
        default=(), alias="objectStores"
    )


class OriginIndexedDbSchema(OriginIndexedDb):
    databases: tuple[IndexedDbDatabaseSchema, ...] = ()


class CookiePartitionKeySchema(CookiePartitionKey):
    pass


class BrowserCookieSchema(BrowserCookie):
    partition_key: CookiePartitionKeySchema | None = Field(
        default=None, alias="partitionKey"
    )


class AuthenticationStateSchema(AuthenticationState):
    cookies: tuple[BrowserCookieSchema, ...] = ()
    local_storage: tuple[OriginLocalStorageSchema, ...] = Field(
        default=(), alias="localStorage"
    )
    indexed_db: tuple[OriginIndexedDbSchema, ...] = Field(alias="indexedDB")


class ScrollPositionSchema(ScrollPosition):
    pass


class BrowserTabStateSchema(BrowserTabState):
    scroll: ScrollPositionSchema = ScrollPositionSchema()
    session_storage: tuple[StorageItemSchema, ...] = Field(
        default=(), alias="sessionStorage"
    )


class BrowserStateSchema(BrowserState):
    tabs: tuple[BrowserTabStateSchema, ...] = ()
