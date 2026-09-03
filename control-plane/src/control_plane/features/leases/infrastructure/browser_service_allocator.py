from uuid import UUID

from control_plane.features.browsers.application.service import BrowserService
from control_plane.features.leases.application.ports import BrowserAllocator


class BrowserServiceAllocator(BrowserAllocator):
    """Adapts the browser feature to the allocator port used by leases."""

    def __init__(self, browsers: BrowserService) -> None:
        self._browsers = browsers

    async def reserve(self, browser_id: UUID) -> None:
        await self._browsers.reserve(browser_id)

    async def release(self, browser_id: UUID) -> None:
        await self._browsers.release(browser_id)
