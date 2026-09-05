from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.browsers.application.ports import BrowserRegistry


class InMemoryBrowserRegistry(BrowserRegistry):
    """Process-local BrowserRegistry implementation for the current MVP."""

    def __init__(self) -> None:
        self._browsers: dict[UUID, Browser] = {}

    def add(self, browser: Browser) -> None:
        self._browsers[browser.id] = browser

    def list(self) -> list[Browser]:
        return list(self._browsers.values())

    def get(self, browser_id: UUID) -> Browser | None:
        return self._browsers.get(browser_id)

    def clear(self) -> None:
        self._browsers.clear()
