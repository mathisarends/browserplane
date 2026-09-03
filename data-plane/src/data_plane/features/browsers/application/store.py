from dataclasses import dataclass
from uuid import UUID

from data_plane.features.browsers.application.models import Browser
from data_plane.features.browsers.application.ports import BrowserProcess


@dataclass(frozen=True, slots=True)
class ManagedBrowser:
    """A browser together with the process and endpoint backing it."""

    browser: Browser
    process: BrowserProcess
    upstream_cdp_url: str


class BrowserStore:
    """Hold the browsers this worker currently runs."""

    def __init__(self) -> None:
        self._browsers: dict[UUID, ManagedBrowser] = {}

    def __len__(self) -> int:
        return len(self._browsers)

    def add(self, browser_id: UUID, managed: ManagedBrowser) -> None:
        self._browsers[browser_id] = managed

    def get(self, browser_id: UUID) -> ManagedBrowser | None:
        return self._browsers.get(browser_id)

    def remove(self, browser_id: UUID) -> ManagedBrowser | None:
        return self._browsers.pop(browser_id, None)

    def ids(self) -> list[UUID]:
        return list(self._browsers)
