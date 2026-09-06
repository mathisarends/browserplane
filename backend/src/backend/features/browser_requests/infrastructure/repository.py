from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import select

from backend.features.browser_requests.application import RequestRepository
from backend.features.browser_requests.domain import BrowserRequest, RequestConflict, RequestStatus
from backend.features.browsers.domain.models import Browser, BrowserSlot, BrowserState
from backend.features.browsers.infrastructure.settings import BrowserPoolSettings
from backend.features.leases.settings import LeaseSettings
from backend.infrastructure.database.models import BrowserModel, BrowserRequestModel, LeaseModel, SessionModel


class SqlRequestRepository(RequestRepository):
    """Every method owns a short transaction; detached values cross the boundary."""

    def __init__(self, factory: async_sessionmaker[AsyncSession], leases: LeaseSettings):
        self._factory = factory
        self._leases = leases

    @staticmethod
    def domain(row: BrowserRequestModel) -> BrowserRequest:
        values = {name: getattr(row, name) for name in BrowserRequest.__dataclass_fields__}
        values["status"] = RequestStatus(row.status)
        return BrowserRequest(**values)

    async def enqueue(self, request: BrowserRequest) -> BrowserRequest:
        async with self._factory.begin() as session:
            await session.execute(insert(BrowserRequestModel).values(
                **{name: getattr(request, name) for name in BrowserRequest.__dataclass_fields__}
            ).on_conflict_do_nothing(index_elements=["id"]))
            row = await session.get(BrowserRequestModel, request.id)
            for field in ("owner_id", "test_run_id", "authentication_profile_id", "browser_checkpoint_id", "resume_session_id"):
                if getattr(row, field) != getattr(request, field):
                    raise RequestConflict("Request ID already belongs to different input")
            return self.domain(row)

    async def get(self, request_id: UUID) -> BrowserRequest:
        async with self._factory() as session:
            row = await session.get(BrowserRequestModel, request_id)
            if row is None:
                raise LookupError("Browser request not found")
            return self.domain(row)

    async def end(self, request_id: UUID, status: RequestStatus) -> BrowserRequest:
        async with self._factory.begin() as session:
            row = await session.get(BrowserRequestModel, request_id, with_for_update=True)
            if row is None:
                raise LookupError("Browser request not found")
            if row.status in (RequestStatus.QUEUED, RequestStatus.PROVISIONING):
                # Deadline and assignment use the same row lock.
                if status != RequestStatus.EXPIRED or row.expires_at <= datetime.now(UTC):
                    row.status = status
            return self.domain(row)

    async def reconcile(self, settings: BrowserPoolSettings) -> None:
        async with self._factory.begin() as session:
            for slot in settings.slots():
                await session.execute(insert(BrowserModel).values(
                    id=slot.id, browser_worker_url=slot.browser_worker_url,
                    state=BrowserState.STOPPED, generation=0, created_at=datetime.now(UTC),
                ).on_conflict_do_nothing(index_elements=["id"]))
                row = await session.get(BrowserModel, slot.id, with_for_update=True)
                # Never redirect a running lease to a different worker.
                if row.state == BrowserState.STOPPED:
                    row.browser_worker_url = slot.browser_worker_url

    async def claim(self) -> tuple[BrowserRequest, Browser] | None:
        async with self._factory.begin() as session:
            now = datetime.now(UTC)
            await session.execute(update(BrowserRequestModel).where(
                BrowserRequestModel.status.in_([RequestStatus.QUEUED, RequestStatus.PROVISIONING]),
                BrowserRequestModel.expires_at <= now,
            ).values(status=RequestStatus.EXPIRED))
            # A leader that died during an external call leaves this reservation.
            # Retry the same generation, cleaning it before remounting state.
            row = await session.scalar(select(BrowserRequestModel).where(
                BrowserRequestModel.browser_id.is_not(None),
                or_(BrowserRequestModel.retry_at.is_(None), BrowserRequestModel.retry_at <= now),
            ).order_by(BrowserRequestModel.created_at, BrowserRequestModel.id)
                .with_for_update(skip_locked=True).limit(1))
            if row is not None:
                browser = await session.get(BrowserModel, row.browser_id, with_for_update=True)
                return self.domain(row), self.browser(browser)
            row = await session.scalar(select(BrowserRequestModel).where(
                BrowserRequestModel.status == RequestStatus.QUEUED,
            ).order_by(BrowserRequestModel.created_at, BrowserRequestModel.id)
                .with_for_update(skip_locked=True).limit(1))
            if row is None:
                return None
            browser = await session.scalar(select(BrowserModel).where(
                BrowserModel.state.in_([BrowserState.STOPPED, BrowserState.READY]),
                ~select(LeaseModel.id).where(
                    LeaseModel.browser_id == BrowserModel.id,
                    LeaseModel.state != "released",
                ).exists(),
            ).order_by(BrowserModel.id).with_for_update(skip_locked=True).limit(1))
            if browser is None:
                return None
            # READY runtimes (e.g. an explicit admin restart) use their current
            # generation. STOPPED slots already received a new generation on release.
            browser.state = BrowserState.STARTING
            row.status = RequestStatus.PROVISIONING
            row.browser_id = browser.id
            return self.domain(row), self.browser(browser)

    @staticmethod
    def browser(row: BrowserModel) -> Browser:
        return Browser(BrowserSlot(row.id, row.browser_worker_url), row.created_at,
                       BrowserState(row.state), row.generation)

    async def finish(self, request_id: UUID, browser: Browser) -> bool:
        async with self._factory.begin() as session:
            row = await session.get(BrowserRequestModel, request_id, with_for_update=True)
            slot = await session.get(BrowserModel, browser.id, with_for_update=True)
            now = datetime.now(UTC)
            if row.status != RequestStatus.PROVISIONING:
                return False
            if row.expires_at <= now:
                row.status = RequestStatus.EXPIRED
                return False
            if slot.state != BrowserState.STARTING or slot.generation != browser.generation:
                return False
            lease_id = row.resume_session_id or uuid4()
            aggregate = await session.get(SessionModel, lease_id, with_for_update=True)
            if row.resume_session_id is not None and (
                aggregate is None or aggregate.status != "suspended"
                or aggregate.expires_at <= now
            ):
                row.status = RequestStatus.CANCELLED
                return False
            expires = now + timedelta(seconds=self._leases.ttl_seconds)
            lease = LeaseModel(id=lease_id, browser_id=slot.id, owner_id=row.owner_id,
                generation=slot.generation, state="active", created_at=now,
                last_renewed_at=now, expires_at=expires,
                reclaim_after=expires + timedelta(seconds=self._leases.grace_period_seconds))
            await session.merge(lease)
            if aggregate is None:
                aggregate = SessionModel(id=lease_id, owner_id=row.owner_id, created_at=now,
                                         status="active", expires_at=expires)
                session.add(aggregate)
            else:
                aggregate.status = "active"
                aggregate.expires_at = expires
                aggregate.browser_checkpoint_id = None
            slot.state = BrowserState.LEASED
            row.status = RequestStatus.ASSIGNED
            row.lease_id = lease_id
            row.browser_id = None
            return True

    async def cleaned(self, request_id: UUID, browser: Browser) -> None:
        async with self._factory.begin() as session:
            row = await session.get(BrowserRequestModel, request_id, with_for_update=True)
            slot = await session.get(BrowserModel, browser.id, with_for_update=True)
            if row.browser_id == browser.id and slot.generation == browser.generation:
                slot.state = BrowserState.STOPPED
                slot.generation += 1
                row.browser_id = None
                row.retry_at = None
                if row.status == RequestStatus.PROVISIONING:
                    row.status = RequestStatus.QUEUED

    async def retry(self, request_id: UUID) -> None:
        async with self._factory.begin() as session:
            row = await session.get(BrowserRequestModel, request_id, with_for_update=True)
            row.retry_at = datetime.now(UTC) + timedelta(seconds=5)
