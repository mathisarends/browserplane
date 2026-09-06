import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.features.browsers.application.service import BrowserService
from backend.features.leases.application.exceptions import LeaseNotFoundException
from backend.features.leases.application.service import LeaseService
from backend.features.sessions.application.exceptions import (
    AuthenticationProfileNotFoundException,
    BrowserCheckpointNotFoundException,
    DownloadNotFoundException,
    SessionNotActiveException,
    SessionNotFoundException,
    SessionNotSuspendedException,
)
from backend.features.sessions.application.ports import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    BrowserRuntime,
    SessionRepository,
)
from backend.features.sessions.domain.models import (
    AuthenticationProfile,
    BrowserCheckpoint,
    BrowserStateDocument,
    Download,
    ResolvedSession,
    Session,
    SessionStatus,
)

logger = logging.getLogger(__name__)


class SessionService:
    """Orchestrates the persistent session aggregate and temporary leases."""

    def __init__(
        self,
        browsers: BrowserService,
        leases: LeaseService,
        sessions: SessionRepository,
        checkpoints: BrowserCheckpointRepository,
        authentication_profiles: AuthenticationProfileRepository,
        browser_state: BrowserRuntime,
        suspension_ttl: timedelta,
    ) -> None:
        self._browsers = browsers
        self._leases = leases
        self._sessions = sessions
        self._checkpoints = checkpoints
        self._authentication_profiles = authentication_profiles
        self._browser_state = browser_state
        self._suspension_ttl = suspension_ttl

    async def remaining_capacity(self) -> int:
        return await self._browsers.remaining_capacity()

    async def get(self, session_id: UUID) -> ResolvedSession:
        session = await self._session(session_id)
        if session.status is not SessionStatus.ACTIVE:
            return ResolvedSession.inactive(session)
        lease = await self._leases.inspect(session_id)
        return ResolvedSession.active(
            session=session,
            lease=lease,
            browser=await self._browsers.get(lease.browser_id),
        )

    async def get_active(self, session_id: UUID) -> ResolvedSession:
        session = await self._session(session_id)
        if session.status is not SessionStatus.ACTIVE:
            raise SessionNotActiveException()
        try:
            lease = await self._leases.get(session_id)
        except LeaseNotFoundException as error:
            raise SessionNotActiveException() from error
        return ResolvedSession.active(
            session=session,
            lease=lease,
            browser=await self._browsers.get(lease.browser_id),
        )

    async def list(self, owner_id: UUID | None = None) -> tuple[ResolvedSession, ...]:
        result: list[ResolvedSession] = []
        for session in await self._sessions.list():
            if session.status is SessionStatus.SUSPENDED and session.is_expired(
                datetime.now(UTC)
            ):
                session = await self._sessions.save(session.close())
            if session.status is SessionStatus.ACTIVE:
                lease = await self._leases.inspect(session.id)
                result.append(
                    ResolvedSession.active(
                        session=session,
                        lease=lease,
                        browser=await self._browsers.get(lease.browser_id),
                    )
                )
            else:
                result.append(ResolvedSession.inactive(session))
        if owner_id is None:
            return tuple(result)
        return tuple(item for item in result if item.owner_id == owner_id)

    async def capture_browser(self, session_id: UUID) -> BrowserStateDocument:
        session = await self.get_active(session_id)
        return await self._browser_state.capture_browser(session.browser)

    async def mount_browser(
        self, session_id: UUID, state: BrowserStateDocument
    ) -> None:
        session = await self.get_active(session_id)
        await self._browser_state.mount_browser(session.browser, state)

    async def mount_authentication_profile(
        self, session_id: UUID, profile_id: UUID
    ) -> None:
        # AsyncSession is request-scoped and does not allow concurrent DB work.
        session = await self.get_active(session_id)
        profile = await self.get_authentication_profile(profile_id)
        await self._browser_state.mount_authentication(
            session.browser, profile.authentication_state
        )

    async def list_downloads(self, session_id: UUID) -> tuple[Download, ...]:
        session = await self.get_active(session_id)
        return await self._browser_state.list_downloads(session.browser)

    async def download_file(
        self, session_id: UUID, download_id: str
    ) -> tuple[str, bytes]:
        session = await self.get_active(session_id)
        downloads = await self._browser_state.list_downloads(session.browser)
        download = next((item for item in downloads if item.id == download_id), None)
        if download is None:
            raise DownloadNotFoundException()
        content = await self._browser_state.download_file(session.browser, download_id)
        return download.filename, content

    async def create_browser_checkpoint(
        self,
        session_id: UUID,
        *,
        authentication_profile_id: UUID | None = None,
    ) -> BrowserCheckpoint:
        session = await self.get_active(session_id)
        if authentication_profile_id is not None:
            await self.get_authentication_profile(authentication_profile_id)
        browser_state = await self._browser_state.capture_browser(session.browser)
        return await self._checkpoints.save(
            BrowserCheckpoint(
                id=uuid4(),
                owner_id=session.owner_id,
                browser_state=browser_state,
                authentication_profile_id=authentication_profile_id,
                created_at=datetime.now(UTC),
            )
        )

    async def get_browser_checkpoint(self, checkpoint_id: UUID) -> BrowserCheckpoint:
        checkpoint = await self._checkpoints.get_by_id(checkpoint_id=checkpoint_id)
        if checkpoint is None:
            raise BrowserCheckpointNotFoundException()
        return checkpoint

    async def list_browser_checkpoints(self) -> tuple[BrowserCheckpoint, ...]:
        return await self._checkpoints.list()

    async def delete_browser_checkpoint(self, checkpoint_id: UUID) -> None:
        if not await self._checkpoints.delete(checkpoint_id):
            raise BrowserCheckpointNotFoundException()

    async def create_authentication_profile(
        self, session_id: UUID, *, name: str
    ) -> AuthenticationProfile:
        session = await self.get_active(session_id)
        state = await self._browser_state.capture_authentication(session.browser)
        return await self._authentication_profiles.save(
            AuthenticationProfile(
                id=uuid4(),
                owner_id=session.owner_id,
                name=name,
                authentication_state=state,
                created_at=datetime.now(UTC),
            )
        )

    async def get_authentication_profile(
        self, profile_id: UUID
    ) -> AuthenticationProfile:
        profile = await self._authentication_profiles.get_by_id(profile_id=profile_id)
        if profile is None:
            raise AuthenticationProfileNotFoundException()
        return profile

    async def list_authentication_profiles(self) -> tuple[AuthenticationProfile, ...]:
        return await self._authentication_profiles.list()

    async def update_authentication_profile(
        self, profile_id: UUID, *, session_id: UUID, name: str
    ) -> AuthenticationProfile:
        current = await self.get_authentication_profile(profile_id)
        session = await self.get_active(session_id)
        state = await self._browser_state.capture_authentication(session.browser)
        return await self._authentication_profiles.save(
            AuthenticationProfile(
                id=current.id,
                owner_id=current.owner_id,
                name=name,
                authentication_state=state,
                created_at=current.created_at,
            )
        )

    async def delete_authentication_profile(self, profile_id: UUID) -> None:
        if not await self._authentication_profiles.delete(profile_id):
            raise AuthenticationProfileNotFoundException()

    async def suspend(self, session_id: UUID) -> ResolvedSession:
        active = await self.get_active(session_id)
        authentication_state, browser_state = await asyncio.gather(
            self._browser_state.capture_authentication(active.browser),
            self._browser_state.capture_browser(active.browser),
        )
        now = datetime.now(UTC)
        profile = await self._authentication_profiles.save(
            AuthenticationProfile(
                id=uuid4(),
                owner_id=active.owner_id,
                name=f"Session {active.id}",
                authentication_state=authentication_state,
                created_at=now,
            )
        )
        checkpoint = await self._checkpoints.save(
            BrowserCheckpoint(
                id=uuid4(),
                owner_id=active.owner_id,
                browser_state=browser_state,
                authentication_profile_id=profile.id,
                created_at=now,
            )
        )
        suspended = await self._sessions.save(
            active.session.suspend(checkpoint.id, now + self._suspension_ttl)
        )
        await self._leases.release(session_id, reason="session_suspended")
        logger.info(
            "Session suspended session_id=%s owner_id=%s browser_id=%s "
            "checkpoint_id=%s expires_at=%s",
            session_id,
            active.owner_id,
            active.browser_id,
            checkpoint.id,
            suspended.expires_at.isoformat() if suspended.expires_at else None,
        )
        return ResolvedSession.inactive(suspended)

    async def close(self, session_id: UUID) -> None:
        aggregate = await self._session(session_id)
        if aggregate.status is SessionStatus.ACTIVE:
            await self._leases.release(session_id, reason="session_closed")
        await self._sessions.save(aggregate.close())
        logger.info(
            "Session closed session_id=%s owner_id=%s previous_status=%s",
            session_id,
            aggregate.owner_id,
            aggregate.status,
        )

    async def renew(self, session_id: UUID) -> ResolvedSession:
        aggregate = await self._session(session_id)
        if aggregate.status is not SessionStatus.ACTIVE:
            raise SessionNotActiveException()
        lease = await self._leases.renew(session_id)
        aggregate = await self._sessions.save(aggregate.renew(lease.expires_at))
        return ResolvedSession.active(
            session=aggregate,
            lease=lease,
            browser=await self._browsers.get(lease.browser_id),
        )

    async def reap_expired(self) -> tuple[UUID, ...]:
        released = await self._leases.reap_due()
        for session_id in released:
            session = await self._sessions.get_by_id(session_id=session_id)
            if session is not None and session.status is SessionStatus.ACTIVE:
                await self._sessions.save(session.close())
                logger.info(
                    "Session reaped session_id=%s owner_id=%s "
                    "reason=lease_expired expired_at=%s",
                    session_id,
                    session.owner_id,
                    session.expires_at.isoformat() if session.expires_at else None,
                )
            else:
                logger.info(
                    "Session lease reaped without an active session session_id=%s "
                    "status=%s",
                    session_id,
                    session.status if session is not None else "missing",
                )
        return released

    async def _session(self, session_id: UUID) -> Session:
        session = await self._sessions.get_by_id(session_id=session_id)
        if session is None:
            raise SessionNotFoundException()
        return session

    async def _suspended_session(self, session_id: UUID) -> Session:
        session = await self._session(session_id)
        if session.status is not SessionStatus.SUSPENDED:
            raise SessionNotSuspendedException()
        if session.is_expired(datetime.now(UTC)):
            await self._sessions.save(session.close())
            raise SessionNotFoundException()
        return session
