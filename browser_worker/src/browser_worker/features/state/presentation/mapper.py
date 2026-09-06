from collections.abc import Iterable

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
from browser_worker.features.state.presentation.schemas import (
    AuthenticationStateSchema,
    BrowserCookieSchema,
    BrowserStateSchema,
    BrowserTabStateSchema,
    CookiePartitionKeySchema,
    IndexedDbDatabaseSchema,
    IndexedDbIndexSchema,
    IndexedDbObjectStoreSchema,
    IndexedDbRecordSchema,
    OriginIndexedDbSchema,
    OriginLocalStorageSchema,
    ScrollPositionSchema,
    StorageItemSchema,
)


def to_browser_state_response(state: BrowserState) -> BrowserStateSchema:
    return BrowserStateSchema(
        tabs=[_to_tab_schema(tab) for tab in state.tabs],
        active_tab_index=state.active_tab_index,
    )


def to_browser_state(schema: BrowserStateSchema) -> BrowserState:
    return BrowserState(
        tabs=tuple(_to_tab(tab) for tab in schema.tabs),
        active_tab_index=schema.active_tab_index,
    )


def to_authentication_state_response(
    state: AuthenticationState,
) -> AuthenticationStateSchema:
    return AuthenticationStateSchema(
        cookies=[_to_cookie_schema(cookie) for cookie in state.cookies],
        local_storage=[
            OriginLocalStorageSchema(
                origin=origin.origin,
                local_storage=_to_item_schemas(origin.local_storage),
            )
            for origin in state.local_storage
        ],
        indexed_db=[_to_indexed_db_schema(origin) for origin in state.indexed_db],
    )


def to_authentication_state(
    schema: AuthenticationStateSchema,
) -> AuthenticationState:
    return AuthenticationState(
        cookies=tuple(_to_cookie(cookie) for cookie in schema.cookies),
        local_storage=tuple(
            OriginLocalStorage(
                origin=origin.origin,
                local_storage=_to_items(origin.local_storage),
            )
            for origin in schema.local_storage
        ),
        indexed_db=tuple(_to_indexed_db(origin) for origin in schema.indexed_db),
    )


def _to_tab_schema(tab: BrowserTabState) -> BrowserTabStateSchema:
    return BrowserTabStateSchema(
        url=tab.url,
        scroll=ScrollPositionSchema(x=tab.scroll.x, y=tab.scroll.y),
        session_storage=_to_item_schemas(tab.session_storage),
    )


def _to_tab(schema: BrowserTabStateSchema) -> BrowserTabState:
    return BrowserTabState(
        url=schema.url,
        scroll=ScrollPosition(x=schema.scroll.x, y=schema.scroll.y),
        session_storage=_to_items(schema.session_storage),
    )


def _to_cookie_schema(cookie: BrowserCookie) -> BrowserCookieSchema:
    return BrowserCookieSchema(
        name=cookie.name,
        value=cookie.value,
        domain=cookie.domain,
        path=cookie.path,
        expires=cookie.expires,
        http_only=cookie.http_only,
        secure=cookie.secure,
        same_site=cookie.same_site,
        priority=cookie.priority,
        source_scheme=cookie.source_scheme,
        source_port=cookie.source_port,
        partition_key=(
            CookiePartitionKeySchema(
                top_level_site=cookie.partition_key.top_level_site,
                has_cross_site_ancestor=cookie.partition_key.has_cross_site_ancestor,
            )
            if cookie.partition_key
            else None
        ),
    )


def _to_cookie(schema: BrowserCookieSchema) -> BrowserCookie:
    return BrowserCookie(
        name=schema.name,
        value=schema.value,
        domain=schema.domain,
        path=schema.path,
        expires=schema.expires,
        http_only=schema.http_only,
        secure=schema.secure,
        same_site=schema.same_site,
        priority=schema.priority,
        source_scheme=schema.source_scheme,
        source_port=schema.source_port,
        partition_key=(
            CookiePartitionKey(
                top_level_site=schema.partition_key.top_level_site,
                has_cross_site_ancestor=schema.partition_key.has_cross_site_ancestor,
            )
            if schema.partition_key
            else None
        ),
    )


def _to_indexed_db_schema(origin: OriginIndexedDb) -> OriginIndexedDbSchema:
    return OriginIndexedDbSchema(
        origin=origin.origin,
        databases=[
            IndexedDbDatabaseSchema(
                name=database.name,
                version=database.version,
                object_stores=[
                    IndexedDbObjectStoreSchema(
                        name=store.name,
                        key_path=_key_path_to_schema(store.key_path),
                        auto_increment=store.auto_increment,
                        indexes=[
                            IndexedDbIndexSchema(
                                name=index.name,
                                key_path=_key_path_to_schema(index.key_path),
                                unique=index.unique,
                                multi_entry=index.multi_entry,
                            )
                            for index in store.indexes
                        ],
                        records=[
                            IndexedDbRecordSchema(key=record.key, value=record.value)
                            for record in store.records
                        ],
                    )
                    for store in database.object_stores
                ],
            )
            for database in origin.databases
        ],
    )


def _to_indexed_db(schema: OriginIndexedDbSchema) -> OriginIndexedDb:
    return OriginIndexedDb(
        origin=schema.origin,
        databases=tuple(
            IndexedDbDatabase(
                name=database.name,
                version=database.version,
                object_stores=tuple(
                    IndexedDbObjectStore(
                        name=store.name,
                        key_path=_key_path_from_schema(store.key_path),
                        auto_increment=store.auto_increment,
                        indexes=tuple(
                            IndexedDbIndex(
                                name=index.name,
                                key_path=_key_path_from_schema(index.key_path),
                                unique=index.unique,
                                multi_entry=index.multi_entry,
                            )
                            for index in store.indexes
                        ),
                        records=tuple(
                            IndexedDbRecord(key=record.key, value=record.value)
                            for record in store.records
                        ),
                    )
                    for store in database.object_stores
                ),
            )
            for database in schema.databases
        ),
    )


def _key_path_to_schema(
    key_path: str | tuple[str, ...] | None,
) -> str | list[str] | None:
    return list(key_path) if isinstance(key_path, tuple) else key_path


def _key_path_from_schema(
    key_path: str | list[str] | None,
) -> str | tuple[str, ...] | None:
    return tuple(key_path) if isinstance(key_path, list) else key_path


def _to_item_schemas(items: Iterable[StorageItem]) -> list[StorageItemSchema]:
    return [StorageItemSchema(name=item.name, value=item.value) for item in items]


def _to_items(schemas: Iterable[StorageItemSchema]) -> tuple[StorageItem, ...]:
    return tuple(StorageItem(name=item.name, value=item.value) for item in schemas)
