import logging
from contextlib import suppress
from uuid import UUID

from backend.features.admin.application.models import PooledBrowser
from backend.features.browsers.application.models import Browser
from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.models import Session, SuspendedSession
from backend.features.sessions.application.service import SessionService

logger = logging.getLogger(__name__)


class AdminService:
    """The operator's view of the pool: what exists, who holds it, tear it down.

    Everything here spans features, which is why it does not live in any of
    them: destroying a browser has to end the session sitting on it first.
    """

    def __init__(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        sessions: SessionService,
    ) -> None:
        self._browsers = browsers
        self._leases = leases
        self._sessions = sessions

    async def list_browsers(self) -> tuple[PooledBrowser, ...]:
        leases = {lease.browser_id: lease for lease in await self._leases.list()}
        return tuple(
            PooledBrowser(browser=browser, lease=leases.get(browser.id))
            for browser in await self._browsers.list()
        )

    async def list_sessions(self) -> tuple[Session | SuspendedSession, ...]:
        return await self._sessions.list()

    async def destroy_browser(self, browser_id: UUID) -> Browser:
        """Stop the browser process and evict whoever was using it."""
        await self._evict(browser_id, reason="browser_destroyed")
        return await self._browsers.destroy(browser_id)

    async def restart_browser(self, browser_id: UUID) -> Browser:
        """Replace the browser process, returning an empty slot to the pool."""
        await self._evict(browser_id, reason="browser_restarted")
        return await self._browsers.restart(browser_id)

    async def _evict(self, browser_id: UUID, *, reason: str) -> None:
        """Drop the lease on a browser we are about to pull out from under it."""
        for lease in await self._leases.list():
            if lease.browser_id != browser_id:
                continue
            logger.info(
                "Evicting session from browser session_id=%s browser_id=%s reason=%s",
                lease.id,
                browser_id,
                reason,
            )
            # A lease that expired between listing and releasing is already gone,
            # which is the outcome we wanted anyway.
            with suppress(LeaseNotFoundException):
                await self._leases.release(lease.id, reason=reason)
