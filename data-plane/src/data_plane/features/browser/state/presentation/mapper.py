from collections.abc import Iterable

from data_plane.features.browser.state.application.models import (
    AuthenticationState,
    BrowserCookie,
    BrowserOriginState,
    BrowserState,
    BrowserTabState,
    ScrollPosition,
    StorageItem,
)
from data_plane.features.browser.state.presentation.schemas import (
    AuthenticationStateSchema,
    BrowserCookieSchema,
    BrowserOriginStateSchema,
    BrowserStateSchema,
    BrowserTabStateSchema,
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
        origins=[
            BrowserOriginStateSchema(
                origin=origin.origin,
                local_storage=_to_item_schemas(origin.local_storage),
            )
            for origin in state.origins
        ],
    )


def to_authentication_state(
    schema: AuthenticationStateSchema,
) -> AuthenticationState:
    return AuthenticationState(
        cookies=tuple(_to_cookie(cookie) for cookie in schema.cookies),
        origins=tuple(
            BrowserOriginState(
                origin=origin.origin,
                local_storage=_to_items(origin.local_storage),
            )
            for origin in schema.origins
        ),
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
    )


def _to_item_schemas(items: Iterable[StorageItem]) -> list[StorageItemSchema]:
    return [StorageItemSchema(name=item.name, value=item.value) for item in items]


def _to_items(schemas: Iterable[StorageItemSchema]) -> tuple[StorageItem, ...]:
    return tuple(StorageItem(name=item.name, value=item.value) for item in schemas)
