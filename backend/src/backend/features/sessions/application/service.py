from contextlib import suppress
from datetime import timedelta
from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.exceptions import (
    NoBrowserAvailableException,
)
from backend.features.sessions.application.models import Session


class SessionService:
    """Frontend-facing view on the browser pool and the lease lifecycle."""

    def __init__(self, browsers: BrowserService, leases: LeaseService) -> None:
        self._browsers = browsers
        self._leases = leases

    async def open(self, owner_id: UUID, ttl: timedelta) -> Session:
        browser = self._pick_available_browser()
        lease = await self._leases.create(browser.id, owner_id, ttl)
        return Session(lease=lease, browser=self._browsers.get(lease.browser_id))

    async def get(self, session_id: UUID) -> Session:
        lease = await self._leases.get(session_id)
        return Session(lease=lease, browser=self._browsers.get(lease.browser_id))

    async def close(self, session_id: UUID) -> None:
        await self._leases.release(session_id)

    async def end(self, session_id: UUID) -> None:
        """
        Close a session whose live connection dropped.

        Nothing but the connection tells us the frontend is gone: a reload or a
        crash never gets around to closing the session itself, and the browser
        would stay leased until the TTL runs out. A session that is already
        closed is the normal case here, not a failure.
        """
        with suppress(LeaseNotFoundException):
            await self.close(session_id)

    async def upstream_tunnel_url(self, session_id: UUID) -> str:
        """Resolve where a session's control channel actually lives."""
        session = await self.get(session_id)
        return session.tunnel_url

    async def upstream_screencast_url(self, session_id: UUID) -> str:
        """Resolve where a session's frame stream actually lives."""
        session = await self.get(session_id)
        return session.screencast_url

    def _pick_available_browser(self) -> Browser:
        for browser in self._browsers.list():
            if browser.is_available:
                return browser
        raise NoBrowserAvailableException()
