from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fakes.session_requests import FakeUnitOfWork

from backend.features.browsers.domain.models import Browser, BrowserSlot
from backend.features.leases.domain.models import Lease, LeaseState
from backend.features.session_requests.application.acquisition import (
    OpenSessionCommand,
    ResumeSessionCommand,
    SessionAcquisition,
)
from backend.features.session_requests.domain import RequestStatus, SessionRequest
from backend.features.sessions.application.exceptions import (
    SessionNotSuspendedException,
)
from backend.features.sessions.domain.models import (
    AuthenticationProfile,
    BrowserCheckpoint,
    ResolvedSession,
    Session,
    SessionStatus,
)


class FakeControlPlane:
    def __init__(self, assigned_session_id: UUID) -> None:
        self.assigned_session_id = assigned_session_id
        self.requests: list[SessionRequest] = []
        self.known: dict[UUID, SessionRequest] = {}

    async def acquire(self, request: SessionRequest) -> UUID:
        self.requests.append(request)
        return self.assigned_session_id

    async def find(self, request_id: UUID) -> SessionRequest | None:
        return self.known.get(request_id)


class FakeAcquisitionSessions:
    def __init__(self, resolved: ResolvedSession) -> None:
        self.resolved = resolved
        self._remaining_capacity = 3
        self.checkpoints: dict[UUID, BrowserCheckpoint] = {}
        self.profiles: dict[UUID, AuthenticationProfile] = {}
        self.requested_sessions: list[UUID] = []
        self.checked_checkpoints: list[UUID] = []
        self.checked_profiles: list[UUID] = []

    async def get_active(self, session_id: UUID) -> ResolvedSession:
        assert session_id == self.resolved.id
        return self.resolved

    async def remaining_capacity(self) -> int:
        return self._remaining_capacity

    async def get(self, session_id: UUID) -> ResolvedSession:
        self.requested_sessions.append(session_id)
        assert session_id == self.resolved.id
        return self.resolved

    async def get_browser_checkpoint(self, checkpoint_id: UUID) -> BrowserCheckpoint:
        self.checked_checkpoints.append(checkpoint_id)
        return self.checkpoints[checkpoint_id]

    async def get_authentication_profile(
        self, profile_id: UUID
    ) -> AuthenticationProfile:
        self.checked_profiles.append(profile_id)
        return self.profiles[profile_id]


def _active_session() -> ResolvedSession:
    session_id = UUID(int=1)
    owner_id = UUID(int=2)
    browser = Browser(BrowserSlot(UUID(int=3), "http://worker"), datetime.now(UTC))
    lease = Lease(
        id=session_id,
        browser_id=browser.id,
        owner_id=owner_id,
        generation=0,
        state=LeaseState.ACTIVE,
        created_at=datetime.now(UTC),
        last_renewed_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(minutes=1),
        reclaim_after=datetime.now(UTC) + timedelta(minutes=2),
    )
    return ResolvedSession.active(
        Session(
            id=session_id,
            owner_id=owner_id,
            status=SessionStatus.ACTIVE,
            created_at=datetime.now(UTC),
            expires_at=lease.expires_at,
        ),
        lease,
        browser,
    )


@pytest.mark.asyncio
async def test_open_checks_referenced_state_before_queueing() -> None:
    resolved = _active_session()
    service = FakeAcquisitionSessions(resolved)
    profile = AuthenticationProfile(
        id=uuid4(),
        owner_id=resolved.owner_id,
        name="Work",
        authentication_state={"cookies": []},
        created_at=datetime.now(UTC),
    )
    checkpoint = BrowserCheckpoint(
        id=uuid4(),
        owner_id=resolved.owner_id,
        browser_state={"tabs": []},
        authentication_profile_id=profile.id,
        created_at=datetime.now(UTC),
    )
    service.profiles[profile.id] = profile
    service.checkpoints[checkpoint.id] = checkpoint
    control = FakeControlPlane(resolved.id)
    acquisition = SessionAcquisition(control, FakeUnitOfWork(service))  # type: ignore[arg-type]

    acquired = await acquisition.open(
        OpenSessionCommand(
            owner_id=resolved.owner_id,
            test_run_id=uuid4(),
            browser_checkpoint_id=checkpoint.id,
        )
    )

    assert acquired.session is resolved
    assert acquired.remaining_capacity == 3
    assert service.checked_checkpoints == [checkpoint.id]
    assert service.checked_profiles == [profile.id]
    assert control.requests[0].browser_checkpoint_id == checkpoint.id


@pytest.mark.asyncio
async def test_resume_uses_suspended_state_or_the_original_pending_request() -> None:
    active = _active_session()
    checkpoint_id = uuid4()
    suspended = replace(
        active.session,
        status=SessionStatus.SUSPENDED,
        browser_checkpoint_id=checkpoint_id,
    )
    service = FakeAcquisitionSessions(ResolvedSession.inactive(suspended))
    service.checkpoints[checkpoint_id] = BrowserCheckpoint(
        id=checkpoint_id,
        owner_id=active.owner_id,
        browser_state={"tabs": []},
        authentication_profile_id=None,
        created_at=datetime.now(UTC),
    )
    control = FakeControlPlane(active.id)
    acquisition = SessionAcquisition(control, FakeUnitOfWork(service))  # type: ignore[arg-type]

    resumed = await acquisition.resume(ResumeSessionCommand(session_id=active.id))
    assert resumed.session is suspended
    assert control.requests[0].resume_session_id == active.id
    assert control.requests[0].browser_checkpoint_id == checkpoint_id

    request_id = uuid4()
    pending = replace(
        control.requests[0],
        id=request_id,
        status=RequestStatus.QUEUED,
    )
    control.known[request_id] = pending
    await acquisition.resume(
        ResumeSessionCommand(session_id=active.id, request_id=request_id)
    )
    assert service.requested_sessions == [active.id]
    assert control.requests[1].browser_checkpoint_id == checkpoint_id


@pytest.mark.asyncio
async def test_resume_rejects_a_session_that_is_not_parked() -> None:
    active = _active_session()
    service = FakeAcquisitionSessions(active)
    acquisition = SessionAcquisition(
        FakeControlPlane(active.id), FakeUnitOfWork(service)  # type: ignore[arg-type]
    )

    with pytest.raises(SessionNotSuspendedException):
        await acquisition.resume(ResumeSessionCommand(session_id=active.id))
