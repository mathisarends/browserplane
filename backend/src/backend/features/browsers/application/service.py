from datetime import UTC, datetime
from uuid import UUID

from backend.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserUnavailableException,
)
from backend.features.browsers.application.models import (
    Browser,
    BrowserState,
)
from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)


class BrowserService:
    """Browser lifecycle: provisioning, inspection and reservation."""

    def __init__(
        self, provisioner: BrowserProvisioner, repository: BrowserRepository
    ) -> None:
        self._provisioner = provisioner
        self._repository = repository

    async def start(self) -> None:
        now = datetime.now(UTC)
        for slot in await self._provisioner.provision():
            await self._repository.save(browser=Browser(slot=slot, created_at=now))

    async def stop(self) -> None:
        await self._repository.delete_all()
        await self._provisioner.deprovision()

    async def create(self) -> Browser:
        raise BrowserCapacityExhaustedException("No unassigned browser slots")

    async def get(self, browser_id: UUID) -> Browser:
        browser = await self._repository.get_by_id(browser_id=browser_id)
        if browser is None:
            raise BrowserNotFoundException()
        return browser

    async def find_available(self) -> Browser | None:
        """The next browser free to be leased, if the pool still has one."""
        return await self._repository.find_available()

    async def destroy(self, browser_id: UUID) -> None:
        browser = await self.get(browser_id)
        browser.state = BrowserState.FAILED
        await self._repository.save(browser=browser)

    async def reset(self, browser_id: UUID) -> Browser:
        browser = await self.get(browser_id)
        browser.state = BrowserState.READY
        return await self._repository.save(browser=browser)

    async def reserve(self, browser_id: UUID) -> None:
        """Mark a browser as taken. Raises when it is not free."""
        browser = await self.get(browser_id)
        if not browser.is_available:
            raise BrowserUnavailableException("Browser is already leased")
        browser.state = BrowserState.LEASED
        await self._repository.save(browser=browser)

    async def release(self, browser_id: UUID) -> None:
        """Return a reserved browser to the pool. Unknown browsers are ignored."""
        browser = await self._repository.get_by_id(browser_id=browser_id)
        if browser is not None and browser.state is BrowserState.LEASED:
            browser.state = BrowserState.READY
            await self._repository.save(browser=browser)
