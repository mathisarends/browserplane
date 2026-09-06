import logging
from collections.abc import AsyncGenerator
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
from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)
from backend.features.browsers.domain.models import (
    Browser,
    BrowserSlot,
    BrowserState,
)

logger = logging.getLogger(__name__)


class BrowserService:
    def __init__(
        self, provisioner: BrowserProvisioner, repository: BrowserRepository
    ) -> None:
        self._provisioner = provisioner
        self._repository = repository

    async def start(self) -> None:
        """Register configured slots without starting worker runtimes."""
        now = datetime.now(UTC)
        for slot in await self._provisioner.provision():
            existing = await self._repository.get_by_id(browser_id=slot.id)
            browser = (
                Browser(slot=slot, created_at=now, state=BrowserState.STOPPED)
                if existing is None
                else Browser(
                    slot=slot,
                    created_at=existing.created_at,
                    state=existing.state,
                    generation=existing.generation,
                )
            )
            await self._repository.save(browser=browser)

    async def stop(self) -> None:
        """Leave worker runtimes and persisted leases available for a new backend."""

    async def create(self) -> Browser:
        raise BrowserCapacityExhaustedException("No unassigned browser slots")

    async def get(self, browser_id: UUID) -> Browser:
        browser = await self._repository.get_by_id(browser_id=browser_id)
        if browser is None:
            raise BrowserNotFoundException()
        return browser

    async def list(self) -> tuple[Browser, ...]:
        return await self._repository.list()

    async def find_available(self) -> Browser | None:
        return await self._repository.find_available()

    async def remaining_capacity(self) -> int:
        return sum(browser.is_available for browser in await self._repository.list())

    async def release(self, browser_id: UUID) -> Browser:
        browser = await self.get(browser_id)
        async with self._browser_worker(browser.slot):
            await self._provisioner.release(browser.slot, browser.generation)
        browser.state = BrowserState.STOPPED
        browser.generation += 1
        logger.info("Browser released browser_id=%s", browser.id)
        return await self._repository.save(browser=browser)

    async def restart(self, browser_id: UUID) -> Browser:
        browser = await self.get(browser_id)
        async with self._browser_worker(browser.slot):
            # Releasing first keeps a restart idempotent: a worker refuses a
            # second browser, but takes a new one once the old process is gone.
            await self._provisioner.release(browser.slot, browser.generation)
            browser.generation += 1
            await self._provisioner.start(browser.slot, browser.generation)
        browser.state = BrowserState.READY
        logger.info("Browser restarted browser_id=%s", browser.id)
        return await self._repository.save(browser=browser)

    async def reset(self, browser_id: UUID) -> Browser:
        browser = await self.get(browser_id)
        browser.state = BrowserState.READY
        return await self._repository.save(browser=browser)

    async def reserve(self, browser_id: UUID) -> int:
        browser = await self.get(browser_id)
        if not browser.is_available:
            raise BrowserUnavailableException("Browser is already leased")
        browser.state = BrowserState.LEASED
        await self._repository.save(browser=browser)
        return browser.generation

    async def recycle(self, browser_id: UUID) -> None:
        """Clean a leased runtime; the next request starts its replacement."""
        browser = await self._repository.get_by_id(browser_id=browser_id)
        if browser is None or browser.state in (
            BrowserState.READY,
            BrowserState.STOPPED,
        ):
            return
        browser.state = BrowserState.RECYCLING
        await self._repository.save(browser=browser)
        try:
            async with self._browser_worker(browser.slot):
                await self._provisioner.release(browser.slot, browser.generation)
                browser.generation += 1
        except Exception:
            browser.state = BrowserState.FAILED
            await self._repository.save(browser=browser)
            raise
        browser.state = BrowserState.STOPPED
        await self._repository.save(browser=browser)

    @asynccontextmanager
    async def _browser_worker(self, slot: BrowserSlot) -> AsyncGenerator[None]:
        """Report a worker that will not cooperate in the pool's own terms."""
        try:
            yield
        except BackendException:
            raise
        except Exception as error:
            logger.warning(
                "Browser provisioning failed browser_id=%s worker=%s error=%s",
                slot.id,
                slot.browser_worker_url,
                error,
            )
            raise BrowserProvisioningException() from error
