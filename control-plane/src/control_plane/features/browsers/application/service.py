import asyncio
from datetime import UTC, datetime
from uuid import UUID

from control_plane.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserUnavailableException,
)
from control_plane.features.browsers.application.models import (
    Browser,
    BrowserState,
)
from control_plane.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRegistry,
)


class BrowserService:
    """Browser lifecycle: provisioning, inspection and reservation."""

    def __init__(
        self, provisioner: BrowserProvisioner, registry: BrowserRegistry
    ) -> None:
        self._provisioner = provisioner
        self._registry = registry
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        now = datetime.now(UTC)
        for slot in await self._provisioner.provision():
            self._registry.add(Browser(slot=slot, created_at=now))

    async def stop(self) -> None:
        self._registry.clear()
        await self._provisioner.deprovision()

    async def create(self) -> Browser:
        raise BrowserCapacityExhaustedException("No unassigned browser slots")

    def list(self) -> list[Browser]:
        return self._registry.list()

    def get(self, browser_id: UUID) -> Browser:
        browser = self._registry.get(browser_id)
        if browser is None:
            raise BrowserNotFoundException()
        return browser

    async def destroy(self, browser_id: UUID) -> None:
        async with self._lock:
            browser = self.get(browser_id)
            browser.state = BrowserState.STOPPING
            browser.state = BrowserState.FAILED

    async def reset(self, browser_id: UUID) -> Browser:
        async with self._lock:
            browser = self.get(browser_id)
            browser.state = BrowserState.STARTING
            browser.state = BrowserState.READY
            return browser

    async def reserve(self, browser_id: UUID) -> None:
        """Mark a browser as taken. Raises when it is not free."""
        async with self._lock:
            browser = self.get(browser_id)
            if not browser.is_available:
                raise BrowserUnavailableException("Browser is already leased")
            browser.state = BrowserState.LEASED

    async def release(self, browser_id: UUID) -> None:
        """Return a reserved browser to the pool. Unknown browsers are ignored."""
        async with self._lock:
            browser = self._registry.get(browser_id)
            if browser is not None and browser.state is BrowserState.LEASED:
                browser.state = BrowserState.READY
