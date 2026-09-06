from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StateModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)


class StorageItem(StateModel):
    name: str
    value: str


class OriginLocalStorage(StateModel):
    origin: str
    local_storage: tuple[StorageItem, ...] = Field(default=(), alias="localStorage")


type IndexedDbKeyPath = str | tuple[str, ...] | None


class IndexedDbIndex(StateModel):
    name: str
    key_path: IndexedDbKeyPath = Field(default=None, alias="keyPath")
    unique: bool = False
    multi_entry: bool = Field(default=False, alias="multiEntry")


class IndexedDbRecord(StateModel):
    key: Any
    value: Any


class IndexedDbObjectStore(StateModel):
    name: str
    key_path: IndexedDbKeyPath = Field(default=None, alias="keyPath")
    auto_increment: bool = Field(default=False, alias="autoIncrement")
    indexes: tuple[IndexedDbIndex, ...] = ()
    records: tuple[IndexedDbRecord, ...] = ()


class IndexedDbDatabase(StateModel):
    name: str
    version: int
    object_stores: tuple[IndexedDbObjectStore, ...] = Field(
        default=(), alias="objectStores"
    )


class OriginIndexedDb(StateModel):
    origin: str
    databases: tuple[IndexedDbDatabase, ...] = ()


class CookiePartitionKey(StateModel):
    top_level_site: str = Field(alias="topLevelSite")
    has_cross_site_ancestor: bool = Field(alias="hasCrossSiteAncestor")


class BrowserCookie(StateModel):
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
    partition_key: CookiePartitionKey | None = Field(default=None, alias="partitionKey")


class AuthenticationState(StateModel):
    cookies: tuple[BrowserCookie, ...] = ()
    local_storage: tuple[OriginLocalStorage, ...] = Field(
        default=(), alias="localStorage"
    )
    indexed_db: tuple[OriginIndexedDb, ...] = Field(default=(), alias="indexedDB")

    @property
    def is_empty(self) -> bool:
        return not self.cookies and not self.local_storage and not self.indexed_db


class ScrollPosition(StateModel):
    x: int = 0
    y: int = 0


class BrowserTabState(StateModel):
    url: str
    scroll: ScrollPosition = ScrollPosition()
    session_storage: tuple[StorageItem, ...] = Field(default=(), alias="sessionStorage")


class BrowserState(StateModel):
    tabs: tuple[BrowserTabState, ...] = ()
    active_tab_index: int = 0
