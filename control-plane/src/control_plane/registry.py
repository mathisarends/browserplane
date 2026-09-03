from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from control_plane.settings import BrowserSlot


@dataclass(frozen=True, slots=True)
class BrowserDescriptor:
    id: UUID
    state: str
    cdp_url: str
    created_at: datetime


@dataclass(slots=True)
class BrowserRecord:
    slot: BrowserSlot
    created_at: datetime
    state: str = "ready"


class BrowserRegistry(Protocol):
    """Storage port for browser records."""

    def add(self, browser: BrowserRecord) -> None: ...

    def list(self) -> list[BrowserRecord]: ...

    def get(self, browser_id: UUID) -> BrowserRecord: ...

    def clear(self) -> None: ...


class InMemoryBrowserRegistry:
    """Process-local BrowserRegistry implementation for the current MVP."""

    def __init__(self) -> None:
        self._browsers: dict[UUID, BrowserRecord] = {}

    def add(self, browser: BrowserRecord) -> None:
        self._browsers[browser.slot.id] = browser

    def list(self) -> list[BrowserRecord]:
        return list(self._browsers.values())

    def get(self, browser_id: UUID) -> BrowserRecord:
        try:
            return self._browsers[browser_id]
        except KeyError as error:
            raise BrowserNotFoundError(browser_id) from error

    def clear(self) -> None:
        self._browsers.clear()


class BrowserNotFoundError(LookupError):
    pass
