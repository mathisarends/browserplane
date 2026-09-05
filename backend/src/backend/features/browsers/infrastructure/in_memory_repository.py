from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.browsers.application.ports import BrowserRepository


class InMemoryBrowserRepository(BrowserRepository):
    """Process-local BrowserRepository, used to run the app without Postgres."""

    def __init__(self) -> None:
        self._browsers: dict[UUID, Browser] = {}

    async def save(self, *, browser: Browser) -> Browser:
        self._browsers[browser.id] = browser
        return browser

    async def get_by_id(self, *, browser_id: UUID) -> Browser | None:
        return self._browsers.get(browser_id)

    async def list_all(self) -> tuple[Browser, ...]:
        return tuple(sorted(self._browsers.values(), key=lambda b: b.created_at))

    async def find_available(self) -> Browser | None:
        return next((b for b in self._browsers.values() if b.is_available), None)

    async def delete_all(self) -> None:
        self._browsers.clear()
