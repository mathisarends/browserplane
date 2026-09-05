from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StorageItem:
    """One key/value pair of a web storage area."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class BrowserOriginState:
    """The localStorage of a single origin."""

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
    """What makes a browser logged in: its cookies and localStorage.

    Shaped like a Playwright ``storage_state`` so it can be handed to a
    Playwright context without conversion.
    """

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
    """A tab as far as it can be restored: where it points and what it holds."""

    url: str
    scroll: ScrollPosition = ScrollPosition()
    session_storage: tuple[StorageItem, ...] = ()


@dataclass(frozen=True, slots=True)
class BrowserState:
    """The restorable state of one browser.

    Tabs are an ordered list and the active tab an index into it; target ids
    are handed out per browser process and worthless after a restart.
    """

    tabs: tuple[BrowserTabState, ...] = ()
    active_tab_index: int = 0
