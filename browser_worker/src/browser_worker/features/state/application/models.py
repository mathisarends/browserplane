from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StorageItem:
    name: str
    value: str


@dataclass(frozen=True, slots=True)
class BrowserOriginState:
    origin: str
    local_storage: tuple[StorageItem, ...] = ()


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


@dataclass(frozen=True, slots=True)
class AuthenticationState:
    cookies: tuple[BrowserCookie, ...] = ()
    origins: tuple[BrowserOriginState, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.cookies and not self.origins


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
