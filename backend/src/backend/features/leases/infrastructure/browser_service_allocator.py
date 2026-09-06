from uuid import UUID

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.ports import BrowserAllocator


class BrowserServiceAllocator(BrowserAllocator):
    """Adapts the browser feature to the allocator port used by leases."""

    def __init__(self, browsers: BrowserService) -> None:
        self._browsers = browsers

    async def reserve(self, browser_id: UUID) -> int:
        return await self._browsers.reserve(browser_id)

    async def recycle(self, browser_id: UUID) -> None:
        await self._browsers.recycle(browser_id)
