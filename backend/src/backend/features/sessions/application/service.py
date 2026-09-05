import asyncio
import logging
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.features.browsers.application.models import Browser
from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.exceptions import (
    NoBrowserAvailableException,
    SessionNotActiveException,
    SessionNotSuspendedException,
)
from backend.features.sessions.application.models import (
    AuthenticationStateDocument,
    BrowserStateDocument,
    BrowserStateSnapshot,
    Session,
    SuspendedSession,
)
from backend.features.sessions.application.ports import (
    BrowserStateGateway,
    BrowserStateSnapshotRepository,
    SuspendedSessionRepository,
)

logger = logging.getLogger(__name__)


class SessionService:
    """Frontend-facing view on the browser pool and the lease lifecycle."""

    def __init__(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        suspensions: SuspendedSessionRepository,
        snapshots: BrowserStateSnapshotRepository,
        browser_state: BrowserStateGateway,
        suspension_ttl: timedelta,
    ) -> None:
        self._browsers = browsers
        self._leases = leases
        self._suspensions = suspensions
        self._snapshots = snapshots
        self._browser_state = browser_state
        self._suspension_ttl = suspension_ttl

    async def open(
        self,
        owner_id: UUID,
        ttl: timedelta,
        authentication_state: AuthenticationStateDocument | None = None,
        browser_state: BrowserStateDocument | None = None,
    ) -> Session:
        browser = await self._pick_available_browser()
        lease = await self._leases.create(browser.id, owner_id, ttl)
        try:
            if authentication_state is not None:
                await self._browser_state.mount_authentication(
                    browser, authentication_state
                )
            if browser_state is not None:
                await self._browser_state.mount_browser(browser, browser_state)
        except Exception:
            with suppress(LeaseNotFoundException):
                await self._leases.release(lease.id, reason="open_state_mount_failed")
            raise
        leased = await self._browsers.get(lease.browser_id)
        return Session(lease=lease, browser=leased)

    async def get(self, session_id: UUID) -> Session | SuspendedSession:
        """Look a session up, whether it currently holds a browser or not."""
        suspended = await self._find_suspended(session_id)
        if suspended is not None:
            return suspended
        return await self.get_active(session_id)

    async def get_active(self, session_id: UUID) -> Session:
        lease = await self._leases.get(session_id)
        browser = await self._browsers.get(lease.browser_id)
        return Session(lease=lease, browser=browser)

    async def list(self) -> tuple[Session | SuspendedSession, ...]:
        """Every session the backend still holds, with a browser or parked."""
        active = [
            Session(lease=lease, browser=await self._browsers.get(lease.browser_id))
            for lease in await self._leases.list()
        ]
        now = datetime.now(UTC)
        parked = [
            suspended
            for suspended in await self._suspensions.list_all()
            if not suspended.is_expired(now)
        ]
        return (*active, *parked)

    async def capture_authentication(
        self, session_id: UUID
    ) -> AuthenticationStateDocument:
        session = await self._active_session(session_id)
        logger.info(
            "Capturing authentication state session_id=%s browser_id=%s",
            session_id,
            session.browser_id,
        )
        return await self._browser_state.capture_authentication(session.browser)

    async def mount_authentication(
        self, session_id: UUID, state: AuthenticationStateDocument
    ) -> None:
        session = await self._active_session(session_id)
        await self._browser_state.mount_authentication(session.browser, state)

    async def capture_browser(self, session_id: UUID) -> BrowserStateDocument:
        session = await self._active_session(session_id)
        logger.info(
            "Capturing browser state session_id=%s browser_id=%s",
            session_id,
            session.browser_id,
        )
        return await self._browser_state.capture_browser(session.browser)

    async def mount_browser(
        self, session_id: UUID, state: BrowserStateDocument
    ) -> None:
        session = await self._active_session(session_id)
        await self._browser_state.mount_browser(session.browser, state)

    async def capture_snapshot(
        self, session_id: UUID, *, name: str, source_browser: str
    ) -> BrowserStateSnapshot:
        session = await self._active_session(session_id)
        authentication_state, browser_state = await asyncio.gather(
            self._browser_state.capture_authentication(session.browser),
            self._browser_state.capture_browser(session.browser),
        )
        return await self._snapshots.save(
            snapshot=BrowserStateSnapshot(
                id=uuid4(),
                owner_id=session.lease.owner_id,
                name=name,
                source_browser=source_browser,
                authentication_state=authentication_state,
                browser_state=browser_state,
                created_at=datetime.now(UTC),
            )
        )

    async def list_snapshots(self) -> tuple[BrowserStateSnapshot, ...]:
        return await self._snapshots.list_all()

    async def suspend(self, session_id: UUID) -> SuspendedSession:
        """Store what the browser holds and give the browser back to the pool.

        The state is captured and written before the lease goes, so a failure
        anywhere in between leaves the session running rather than empty.
        """
        session = await self._active_session(session_id)
        authentication_state, browser_state = await asyncio.gather(
            self._browser_state.capture_authentication(session.browser),
            self._browser_state.capture_browser(session.browser),
        )
        now = datetime.now(UTC)
        suspended = await self._suspensions.save(
            suspended=SuspendedSession(
                id=session.id,
                owner_id=session.lease.owner_id,
                authentication_state=authentication_state,
                browser_state=browser_state,
                created_at=now,
                expires_at=now + self._suspension_ttl,
            )
        )
        await self._leases.release(session_id, reason="session_suspended")
        return suspended

    async def resume(self, session_id: UUID, ttl: timedelta) -> Session:
        """Put a suspended session back onto whichever browser is free now.

        The lease keeps the old session id, so the tunnel and screencast paths
        a client was handed before suspending still point at this session.
        """
        suspended = await self._suspended_session(session_id)
        browser = await self._pick_available_browser()
        lease = await self._leases.create(
            browser.id,
            suspended.owner_id,
            ttl,
            lease_id=suspended.id,
        )
        try:
            # Authentication must be present before restored tabs navigate.
            await self._browser_state.mount_authentication(
                browser, suspended.authentication_state
            )
            await self._browser_state.mount_browser(browser, suspended.browser_state)
        except Exception:
            # The state is still stored, so the session stays resumable.
            with suppress(LeaseNotFoundException):
                await self._leases.release(lease.id, reason="resume_state_mount_failed")
            raise
        await self._suspensions.delete(session_id=suspended.id)
        leased = await self._browsers.get(lease.browser_id)
        return Session(lease=lease, browser=leased)

    async def close(self, session_id: UUID) -> None:
        if await self._find_suspended(session_id) is not None:
            await self._suspensions.delete(session_id=session_id)
            return
        await self._leases.release(session_id, reason="session_closed")

    async def upstream_cdp_url(self, session_id: UUID) -> str:
        """Resolve the internal CDP stream used by the backend RPC endpoint."""
        session = await self._active_session(session_id)
        return session.cdp_url

    async def upstream_screencast_url(self, session_id: UUID) -> str:
        """Resolve where a session's frame stream actually lives."""
        session = await self._active_session(session_id)
        return session.screencast_url

    async def upstream_fmp4_screencast_url(self, session_id: UUID) -> str:
        """Resolve the encoded frame stream without replacing the raw stream."""
        session = await self._active_session(session_id)
        return session.fmp4_screencast_url

    async def _active_session(self, session_id: UUID) -> Session:
        if await self._find_suspended(session_id) is not None:
            raise SessionNotActiveException()
        return await self.get_active(session_id)

    async def _suspended_session(self, session_id: UUID) -> SuspendedSession:
        suspended = await self._find_suspended(session_id)
        if suspended is not None:
            return suspended
        # An unknown session must read as gone, not as "not suspended".
        await self.get_active(session_id)
        raise SessionNotSuspendedException()

    async def _find_suspended(self, session_id: UUID) -> SuspendedSession | None:
        """Drop a suspension nobody came back for, the way leases expire."""
        suspended = await self._suspensions.get_by_id(session_id=session_id)
        if suspended is None:
            return None
        if suspended.is_expired(datetime.now(UTC)):
            await self._suspensions.delete(session_id=suspended.id)
            return None
        return suspended

    async def _pick_available_browser(self) -> Browser:
        browser = await self._browsers.find_available()
        if browser is None:
            raise NoBrowserAvailableException()
        return browser
