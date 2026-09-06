from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class StorageItem:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class OriginLocalStorage:
    origin: str
    local_storage: tuple[StorageItem, ...] = ()


type IndexedDbKeyPath = str | tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class IndexedDbIndex:
    name: str
    key_path: IndexedDbKeyPath = None
    unique: bool = False
    multi_entry: bool = False


@dataclass(frozen=True, slots=True)
class IndexedDbRecord:
    key: Any
    value: Any


@dataclass(frozen=True, slots=True)
class IndexedDbObjectStore:
    name: str
    key_path: IndexedDbKeyPath = None
    auto_increment: bool = False
    indexes: tuple[IndexedDbIndex, ...] = ()
    records: tuple[IndexedDbRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class IndexedDbDatabase:
    name: str
    version: int
    object_stores: tuple[IndexedDbObjectStore, ...] = ()


@dataclass(frozen=True, slots=True)
class OriginIndexedDb:
    origin: str
    databases: tuple[IndexedDbDatabase, ...] = ()


@dataclass(frozen=True, slots=True)
class CookiePartitionKey:
    top_level_site: str
    has_cross_site_ancestor: bool


@dataclass(frozen=True, slots=True)
class BrowserCookie:
    name: str
    value: str
    domain: str
    path: str
    expires: float | None = None
    http_only: bool = False
    secure: bool = False
    same_site: str | None = None
    priority: str | None = None
    source_scheme: str | None = None
    source_port: int | None = None
    partition_key: CookiePartitionKey | None = None


@dataclass(frozen=True, slots=True)
class AuthenticationState:
    cookies: tuple[BrowserCookie, ...] = ()
    local_storage: tuple[OriginLocalStorage, ...] = ()
    indexed_db: tuple[OriginIndexedDb, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.cookies and not self.local_storage and not self.indexed_db


@dataclass(frozen=True, slots=True)
class ScrollPosition:
    x: int = 0
    y: int = 0


@dataclass(frozen=True, slots=True)
class BrowserTabState:
    url: str
    scroll: ScrollPosition = ScrollPosition()
    session_storage: tuple[StorageItem, ...] = ()


@dataclass(frozen=True, slots=True)
class BrowserState:
    tabs: tuple[BrowserTabState, ...] = ()
    active_tab_index: int = 0
