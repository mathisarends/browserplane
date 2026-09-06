from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from backend.features.session_requests.application.control_plane import ControlPlane
from backend.features.session_requests.domain import RequestStatus, SessionRequest
from backend.features.sessions.application.exceptions import (
    SessionNotSuspendedException,
)
from backend.features.sessions.application.service import SessionService
from backend.features.sessions.domain.models import ResolvedSession, SessionStatus
from backend.shared.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class OpenSessionCommand:
    owner_id: UUID
    request_id: UUID | None = None
    timeout_seconds: float = 60
    test_run_id: UUID | None = None
    authentication_profile_id: UUID | None = None
    browser_checkpoint_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResumeSessionCommand:
    session_id: UUID
    request_id: UUID | None = None
    timeout_seconds: float = 60


@dataclass(frozen=True, slots=True)
class AcquiredSession:
    """A session that just took a browser, and what the pool has left."""

    session: ResolvedSession
    remaining_capacity: int


class SessionAcquisition:
    """Turns a session request into the session it was asking for.

    Opening and resuming differ only in where the request's inputs come from:
    a caller states them, a suspended session already carries them. Both then
    queue, wait, and read back the session the assignment created.

    Every database access sits inside its own unit of work. The wait between
    them can last minutes and holds no session, no transaction and no pooled
    connection.
    """

    def __init__(
        self,
        control: ControlPlane,
        sessions: UnitOfWork[SessionService],
    ) -> None:
        self._control = control
        self._sessions = sessions

    async def open(self, command: OpenSessionCommand) -> AcquiredSession:
        if await self._is_new(command.request_id):
            async with self._sessions() as sessions:
                await self._check_state(
                    sessions,
                    command.authentication_profile_id,
                    command.browser_checkpoint_id,
                )
        session_id = await self._control.acquire(
            self._queued(
                request_id=command.request_id,
                owner_id=command.owner_id,
                timeout_seconds=command.timeout_seconds,
                test_run_id=command.test_run_id,
                authentication_profile_id=command.authentication_profile_id,
                browser_checkpoint_id=command.browser_checkpoint_id,
            )
        )
        async with self._sessions() as sessions:
            return AcquiredSession(
                session=await sessions.get_active(session_id),
                remaining_capacity=await sessions.remaining_capacity(),
            )

    async def resume(self, command: ResumeSessionCommand) -> ResolvedSession:
        pending = (
            await self._control.find(command.request_id)
            if command.request_id is not None
            else None
        )
        if pending is not None:
            # A retry of an attempt that may already have resumed the session,
            # which clears the checkpoint off the aggregate. Only the stored
            # request still knows which state this resume was queued for.
            owner_id = pending.owner_id
            browser_checkpoint_id = pending.browser_checkpoint_id
        else:
            async with self._sessions() as sessions:
                suspended = await sessions.get(command.session_id)
                if suspended.session.status is not SessionStatus.SUSPENDED:
                    raise SessionNotSuspendedException()
                owner_id = suspended.owner_id
                browser_checkpoint_id = suspended.session.browser_checkpoint_id
                await self._check_state(sessions, None, browser_checkpoint_id)
        session_id = await self._control.acquire(
            self._queued(
                request_id=command.request_id,
                owner_id=owner_id,
                timeout_seconds=command.timeout_seconds,
                browser_checkpoint_id=browser_checkpoint_id,
                resume_session_id=command.session_id,
            )
        )
        async with self._sessions() as sessions:
            return await sessions.get_active(session_id)

    async def _is_new(self, request_id: UUID | None) -> bool:
        """A known request keeps the inputs it was checked and queued with."""
        if request_id is None:
            return True
        return await self._control.find(request_id) is None

    @staticmethod
    async def _check_state(
        sessions: SessionService,
        authentication_profile_id: UUID | None,
        browser_checkpoint_id: UUID | None,
    ) -> None:
        """Reject unusable state now instead of after a wait, or in a dispatcher."""
        checkpoint = (
            await sessions.get_browser_checkpoint(browser_checkpoint_id)
            if browser_checkpoint_id is not None
            else None
        )
        profile_id = authentication_profile_id or (
            checkpoint.authentication_profile_id if checkpoint is not None else None
        )
        if profile_id is not None:
            await sessions.get_authentication_profile(profile_id)

    @staticmethod
    def _queued(
        *,
        request_id: UUID | None,
        owner_id: UUID,
        timeout_seconds: float,
        test_run_id: UUID | None = None,
        authentication_profile_id: UUID | None = None,
        browser_checkpoint_id: UUID | None = None,
        resume_session_id: UUID | None = None,
    ) -> SessionRequest:
        now = datetime.now(UTC)
        return SessionRequest(
            id=request_id or uuid4(),
            owner_id=owner_id,
            status=RequestStatus.QUEUED,
            created_at=now,
            expires_at=now + timedelta(seconds=timeout_seconds),
            test_run_id=test_run_id,
            authentication_profile_id=authentication_profile_id,
            browser_checkpoint_id=browser_checkpoint_id,
            resume_session_id=resume_session_id,
        )
