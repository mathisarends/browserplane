from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from backend.features.browsers.application.ports import (
    BrowserProvisioner,
    BrowserRepository,
)
from backend.features.browsers.domain.models import BrowserState
from backend.features.leases.application.ports import LeaseStore
from backend.features.leases.domain.models import Lease, LeaseState
from backend.features.leases.settings import LeaseSettings
from backend.features.session_requests.application.ports import SessionRequestRepository
from backend.features.session_requests.domain import (
    RequestStatus,
    SessionRequest,
    SessionRequestNotFoundException,
)
from backend.features.sessions.application.ports import (
    AuthenticationProfileRepository,
    BrowserCheckpointRepository,
    BrowserRuntime,
    SessionRepository,
)
from backend.features.sessions.domain.models import Session, SessionStatus


class InMemorySessionRequestRepository(SessionRequestRepository):
    """Request queue fake whose state can be advanced by a test dispatcher."""

    def __init__(self) -> None:
        self.requests: dict[UUID, SessionRequest] = {}

    async def enqueue(self, request: SessionRequest) -> SessionRequest:
        self.requests.setdefault(request.id, request)
        return self.requests[request.id]

    async def get(self, request_id: UUID) -> SessionRequest:
        try:
            return self.requests[request_id]
        except KeyError as error:
            raise SessionRequestNotFoundException() from error

    async def end(self, request_id: UUID, status: RequestStatus) -> SessionRequest:
        request = await self.get(request_id)
        if not request.is_terminal:
            request = replace(request, status=status)
            self.requests[request_id] = request
        return request

    def assign(self, request_id: UUID, session_id: UUID) -> None:
        request = self.requests[request_id]
        self.requests[request_id] = replace(
            request, status=RequestStatus.ASSIGNED, session_id=session_id
        )


class ImmediateSessionRequestRepository(InMemorySessionRequestRepository):
    """Test-only dispatcher that assigns each queued request immediately."""

    def __init__(
        self,
        browsers: BrowserRepository,
        provisioner: BrowserProvisioner,
        leases: LeaseStore,
        sessions: SessionRepository,
        runtime: BrowserRuntime,
        checkpoints: BrowserCheckpointRepository,
        profiles: AuthenticationProfileRepository,
    ) -> None:
        super().__init__()
        self._browsers = browsers
        self._provisioner = provisioner
        self._leases = leases
        self._sessions = sessions
        self._runtime = runtime
        self._checkpoints = checkpoints
        self._profiles = profiles
        settings = LeaseSettings()
        self._ttl = timedelta(seconds=settings.ttl_seconds)
        self._grace_period = timedelta(seconds=settings.grace_period_seconds)

    async def enqueue(self, request: SessionRequest) -> SessionRequest:
        existing = self.requests.get(request.id)
        if existing is not None:
            return existing
        browser = await self._browsers.find_available()
        if browser is None:
            self.requests[request.id] = request
            return request

        now = datetime.now(UTC)
        await self._provisioner.start(browser.slot, browser.generation)
        await self._runtime.clear_downloads(browser)
        checkpoint = (
            await self._checkpoints.get_by_id(
                checkpoint_id=request.browser_checkpoint_id
            )
            if request.browser_checkpoint_id is not None
            else None
        )
        profile_id = request.authentication_profile_id or (
            checkpoint.authentication_profile_id if checkpoint is not None else None
        )
        if profile_id is not None:
            profile = await self._profiles.get_by_id(profile_id=profile_id)
            assert profile is not None
            await self._runtime.mount_authentication(
                browser, profile.authentication_state
            )
        if checkpoint is not None:
            await self._runtime.mount_browser(browser, checkpoint.browser_state)

        browser.state = BrowserState.LEASED
        await self._browsers.save(browser=browser)
        expires_at = now + self._ttl
        lease = Lease(
            id=request.resume_session_id or request.id,
            browser_id=browser.id,
            owner_id=request.owner_id,
            generation=browser.generation,
            state=LeaseState.ACTIVE,
            created_at=now,
            last_renewed_at=now,
            expires_at=expires_at,
            reclaim_after=expires_at + self._grace_period,
        )
        await self._leases.save(lease)
        if request.resume_session_id is None:
            session = Session(
                id=lease.id,
                owner_id=request.owner_id,
                status=SessionStatus.ACTIVE,
                created_at=now,
                expires_at=expires_at,
            )
        else:
            suspended = await self._sessions.get_by_id(
                session_id=request.resume_session_id
            )
            assert suspended is not None
            session = suspended.resume(expires_at)
        await self._sessions.save(session)
        assigned = replace(
            request,
            status=RequestStatus.ASSIGNED,
            session_id=session.id,
        )
        self.requests[request.id] = assigned
        return assigned


class FakeUnitOfWork[ServiceT]:
    """Yields one in-memory application service without transaction machinery."""

    def __init__(self, service: ServiceT) -> None:
        self.service = service
        self.entries = 0

    @asynccontextmanager
    async def __call__(self):
        self.entries += 1
        yield self.service
