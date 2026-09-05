from datetime import timedelta
from uuid import UUID

from gateway.features.sessions.application.exceptions import (
    NoBrowserAvailableException,
)
from gateway.features.sessions.application.models import Session
from gateway.features.sessions.application.ports import BrowserCatalog, LeaseBroker


class SessionService:
    """Turns the control plane's browser and lease APIs into one session."""

    def __init__(self, catalog: BrowserCatalog, leases: LeaseBroker) -> None:
        self._catalog = catalog
        self._leases = leases

    async def open(self, owner_id: UUID, ttl: timedelta) -> Session:
        browser_id = await self._pick_available_browser()
        lease = await self._leases.create(browser_id, owner_id, ttl)
        return Session(lease=lease, endpoints=await self._catalog.endpoints(browser_id))

    async def get(self, session_id: UUID) -> Session:
        lease = await self._leases.get(session_id)
        endpoints = await self._catalog.endpoints(lease.browser_id)
        return Session(lease=lease, endpoints=endpoints)

    async def upstream_tunnel_url(self, session_id: UUID) -> str:
        """Resolve where a session's control channel actually lives."""
        session = await self.get(session_id)
        return session.endpoints.tunnel_url

    async def upstream_screencast_url(self, session_id: UUID) -> str:
        """Resolve where a session's frame stream actually lives."""
        session = await self.get(session_id)
        return session.endpoints.screencast_url

    async def close(self, session_id: UUID) -> None:
        await self._leases.release(session_id)

    async def _pick_available_browser(self) -> UUID:
        for browser in await self._catalog.list():
            if browser.is_available:
                return browser.id
        raise NoBrowserAvailableException()
