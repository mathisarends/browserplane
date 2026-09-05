import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

from backend.exceptions import BackendException
from backend.features.browsers.application.exceptions import (
    BrowserCapacityExhaustedException,
    BrowserNotFoundException,
    BrowserProvisioningException,
    BrowserUnavailableException,
)
from backend.features.browsers.application.models import (
    Browser,
    BrowserSlot,
    BrowserState,
)
from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)

logger = logging.getLogger(__name__)


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

    async def list(self) -> tuple[Browser, ...]:
        """The whole pool, for operators who need to see it, not lease from it."""
        return await self._repository.list_all()

    async def find_available(self) -> Browser | None:
        """The next browser free to be leased, if the pool still has one."""
        return await self._repository.find_available()

    async def remaining_capacity(self) -> int:
        """How many healthy pool slots can still be leased right now."""
        return sum(
            browser.is_available for browser in await self._repository.list_all()
        )

    async def destroy(self, browser_id: UUID) -> Browser:
        """Tear the browser process down. The slot survives, empty, until restarted."""
        browser = await self.get(browser_id)
        async with self._data_plane(browser.slot):
            await self._provisioner.stop(browser.slot)
        browser.state = BrowserState.STOPPED
        logger.info("Browser destroyed browser_id=%s", browser.id)
        return await self._repository.save(browser=browser)

    async def restart(self, browser_id: UUID) -> Browser:
        """Put a fresh browser process behind a slot, whatever state it was in."""
        browser = await self.get(browser_id)
        async with self._data_plane(browser.slot):
            # Stopping first keeps a restart idempotent: a worker refuses a
            # second browser, but takes a new one once the old process is gone.
            await self._provisioner.stop(browser.slot)
            await self._provisioner.start(browser.slot)
        browser.state = BrowserState.READY
        logger.info("Browser restarted browser_id=%s", browser.id)
        return await self._repository.save(browser=browser)

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

    @asynccontextmanager
    async def _data_plane(self, slot: BrowserSlot) -> AsyncIterator[None]:
        """Report a worker that will not cooperate in the pool's own terms."""
        try:
            yield
        except BackendException:
            raise
        except Exception as error:
            logger.warning(
                "Browser provisioning failed browser_id=%s worker=%s error=%s",
                slot.id,
                slot.data_plane_url,
                error,
            )
            raise BrowserProvisioningException() from error
