from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class StateModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
    )


class StorageItem(StateModel):
    name: str
    value: str


class OriginLocalStorage(StateModel):
    origin: str
    local_storage: tuple[StorageItem, ...] = ()


type IndexedDbKeyPath = str | tuple[str, ...] | None


class IndexedDbIndex(StateModel):
    name: str
    key_path: IndexedDbKeyPath = None
    unique: bool = False
    multi_entry: bool = False


class IndexedDbRecord(StateModel):
    key: Any
    value: Any


class IndexedDbObjectStore(StateModel):
    name: str
    key_path: IndexedDbKeyPath = None
    auto_increment: bool = False
    indexes: tuple[IndexedDbIndex, ...] = ()
    records: tuple[IndexedDbRecord, ...] = ()


class IndexedDbDatabase(StateModel):
    name: str
    version: int
    object_stores: tuple[IndexedDbObjectStore, ...] = ()


class OriginIndexedDb(StateModel):
    origin: str
    databases: tuple[IndexedDbDatabase, ...] = ()


class CookiePartitionKey(StateModel):
    top_level_site: str
    has_cross_site_ancestor: bool


class BrowserCookie(StateModel):
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


class AuthenticationState(StateModel):
    cookies: tuple[BrowserCookie, ...] = ()
    local_storage: tuple[OriginLocalStorage, ...] = ()
    # Preserve the Web API spelling; generic camel case would produce indexedDb.
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
    session_storage: tuple[StorageItem, ...] = ()


class BrowserState(StateModel):
    tabs: tuple[BrowserTabState, ...] = ()
    # Browser state intentionally uses snake_case in the external API.
    active_tab_index: int = Field(default=0, alias="active_tab_index")
