from pydantic import ConfigDict

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


def _api_alias(field: str) -> str:
    return _API_ALIASES.get(field, field)


_API_ALIASES = {
    "auto_increment": "autoIncrement",
    "has_cross_site_ancestor": "hasCrossSiteAncestor",
    "http_only": "httpOnly",
    "indexed_db": "indexedDB",
    "key_path": "keyPath",
    "local_storage": "localStorage",
    "multi_entry": "multiEntry",
    "object_stores": "objectStores",
    "partition_key": "partitionKey",
    "same_site": "sameSite",
    "session_storage": "sessionStorage",
    "source_port": "sourcePort",
    "source_scheme": "sourceScheme",
    "top_level_site": "topLevelSite",
}


_API_MODEL_CONFIG = ConfigDict(
    alias_generator=_api_alias,
    populate_by_name=True,
    frozen=True,
)


class StorageItemSchema(StorageItem):
    model_config = _API_MODEL_CONFIG


class OriginLocalStorageSchema(OriginLocalStorage):
    model_config = _API_MODEL_CONFIG
    local_storage: tuple[StorageItemSchema, ...] = ()


class IndexedDbIndexSchema(IndexedDbIndex):
    model_config = _API_MODEL_CONFIG


class IndexedDbRecordSchema(IndexedDbRecord):
    model_config = _API_MODEL_CONFIG


class IndexedDbObjectStoreSchema(IndexedDbObjectStore):
    model_config = _API_MODEL_CONFIG
    indexes: tuple[IndexedDbIndexSchema, ...] = ()
    records: tuple[IndexedDbRecordSchema, ...] = ()


class IndexedDbDatabaseSchema(IndexedDbDatabase):
    model_config = _API_MODEL_CONFIG
    object_stores: tuple[IndexedDbObjectStoreSchema, ...] = ()


class OriginIndexedDbSchema(OriginIndexedDb):
    model_config = _API_MODEL_CONFIG
    databases: tuple[IndexedDbDatabaseSchema, ...] = ()


class CookiePartitionKeySchema(CookiePartitionKey):
    model_config = _API_MODEL_CONFIG


class BrowserCookieSchema(BrowserCookie):
    model_config = _API_MODEL_CONFIG
    partition_key: CookiePartitionKeySchema | None = None


class AuthenticationStateSchema(AuthenticationState):
    model_config = _API_MODEL_CONFIG
    cookies: tuple[BrowserCookieSchema, ...] = ()
    local_storage: tuple[OriginLocalStorageSchema, ...] = ()
    indexed_db: tuple[OriginIndexedDbSchema, ...]


class ScrollPositionSchema(ScrollPosition):
    model_config = _API_MODEL_CONFIG


class BrowserTabStateSchema(BrowserTabState):
    model_config = _API_MODEL_CONFIG
    scroll: ScrollPositionSchema = ScrollPositionSchema()
    session_storage: tuple[StorageItemSchema, ...] = ()


class BrowserStateSchema(BrowserState):
    model_config = _API_MODEL_CONFIG
    tabs: tuple[BrowserTabStateSchema, ...] = ()
