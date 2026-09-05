from pydantic import BaseModel, ConfigDict, Field


class PlaywrightModel(BaseModel):
    """Accepts and emits the camelCase names Playwright's storage state uses."""

    model_config = ConfigDict(populate_by_name=True)


class StorageItemSchema(PlaywrightModel):
    name: str
    value: str


class BrowserOriginStateSchema(PlaywrightModel):
    origin: str
    local_storage: list[StorageItemSchema] = Field(default=[], alias="localStorage")


class BrowserCookieSchema(PlaywrightModel):
    name: str
    value: str
    domain: str
    path: str
    expires: float | None = None
    http_only: bool = Field(default=False, alias="httpOnly")
    secure: bool = False
    same_site: str | None = Field(default=None, alias="sameSite")


class AuthenticationStateSchema(PlaywrightModel):
    """A Playwright ``storage_state``: what makes the browser logged in."""

    cookies: list[BrowserCookieSchema] = []
    origins: list[BrowserOriginStateSchema] = []


class ScrollPositionSchema(PlaywrightModel):
    x: int = 0
    y: int = 0


class BrowserTabStateSchema(PlaywrightModel):
    url: str
    scroll: ScrollPositionSchema = ScrollPositionSchema()
    session_storage: list[StorageItemSchema] = Field(default=[], alias="sessionStorage")


class BrowserStateSchema(PlaywrightModel):
    """The restorable state of a browser; the body of both state endpoints."""

    tabs: list[BrowserTabStateSchema] = []
    active_tab_index: int = 0
    authentication: AuthenticationStateSchema = AuthenticationStateSchema()
