from dataclasses import dataclass
from enum import StrEnum


class BrowserState(StrEnum):
    READY = "ready"


@dataclass(frozen=True, slots=True)
class Browser:
    """A Chromium instance owned by this worker."""

    id: str
    state: BrowserState
    cdp_url: str


@dataclass(frozen=True, slots=True)
class Capacity:
    total: int
    available: int
