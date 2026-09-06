from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StateModel(BaseModel):
    """Accept API aliases as well as snake_case Python field names."""

    model_config = ConfigDict(populate_by_name=True)


class StorageItemSchema(StateModel):
    name: str
    value: str


class OriginLocalStorageSchema(StateModel):
    origin: str
    local_storage: list[StorageItemSchema] = Field(default=[], alias="localStorage")


class IndexedDbIndexSchema(StateModel):
    name: str
    key_path: str | list[str] | None = Field(default=None, alias="keyPath")
    unique: bool = False
    multi_entry: bool = Field(default=False, alias="multiEntry")


class IndexedDbRecordSchema(StateModel):
    key: Any
    value: Any


class IndexedDbObjectStoreSchema(StateModel):
    name: str
    key_path: str | list[str] | None = Field(default=None, alias="keyPath")
    auto_increment: bool = Field(default=False, alias="autoIncrement")
    indexes: list[IndexedDbIndexSchema] = []
    records: list[IndexedDbRecordSchema] = []


class IndexedDbDatabaseSchema(StateModel):
    name: str
    version: int
    object_stores: list[IndexedDbObjectStoreSchema] = Field(
        default=[], alias="objectStores"
    )


class OriginIndexedDbSchema(StateModel):
    origin: str
    databases: list[IndexedDbDatabaseSchema] = []


class CookiePartitionKeySchema(StateModel):
    top_level_site: str = Field(alias="topLevelSite")
    has_cross_site_ancestor: bool = Field(alias="hasCrossSiteAncestor")


class BrowserCookieSchema(StateModel):
    name: str
    value: str
    domain: str
    path: str
    expires: float | None = None
    http_only: bool = Field(default=False, alias="httpOnly")
    secure: bool = False
    same_site: str | None = Field(default=None, alias="sameSite")
    priority: str | None = None
    source_scheme: str | None = Field(default=None, alias="sourceScheme")
    source_port: int | None = Field(default=None, alias="sourcePort")
    partition_key: CookiePartitionKeySchema | None = Field(
        default=None, alias="partitionKey"
    )


class AuthenticationStateSchema(StateModel):
    """Portable persistent browser state used to rehydrate a login."""

    cookies: list[BrowserCookieSchema] = []
    local_storage: list[OriginLocalStorageSchema] = Field(
        default=[], alias="localStorage"
    )
    indexed_db: list[OriginIndexedDbSchema] = Field(alias="indexedDB")


class ScrollPositionSchema(StateModel):
    x: int = 0
    y: int = 0


class BrowserTabStateSchema(StateModel):
    url: str
    scroll: ScrollPositionSchema = ScrollPositionSchema()
    session_storage: list[StorageItemSchema] = Field(default=[], alias="sessionStorage")


class BrowserStateSchema(StateModel):
    """Restorable tabs and their UI state, independent of authentication."""

    tabs: list[BrowserTabStateSchema] = []
    active_tab_index: int = 0
