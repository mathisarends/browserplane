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


class BrowserCookieSchema(StateModel):
    name: str
    value: str
    domain: str
    path: str
    expires: float | None = None
    http_only: bool = Field(default=False, alias="httpOnly")
    secure: bool = False
    same_site: str | None = Field(default=None, alias="sameSite")


class AuthenticationStateSchema(StateModel):
    """A Playwright ``storage_state``: what makes the browser logged in."""

    cookies: list[BrowserCookieSchema] = []
    local_storage: list[OriginLocalStorageSchema] = Field(
        default=[], alias="localStorage"
    )


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
