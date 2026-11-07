import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fakes.session_requests import InMemorySessionRequestRepository

from backend.features.session_requests.application import ControlPlane, Wakeups
from backend.features.session_requests.domain import (
    RequestStatus,
    SessionRequest,
    SessionRequestCancelledException,
    SessionRequestNotFoundException,
    SessionRequestTimedOutException,
)


def _request(
    *, request_id: UUID | None = None, expires_at: datetime | None = None
) -> SessionRequest:
    now = datetime.now(UTC)
    return SessionRequest(
        id=request_id if request_id is not None else UUID(int=10),
        owner_id=UUID(int=11),
        status=RequestStatus.QUEUED,
        created_at=now,
        expires_at=expires_at or now + timedelta(minutes=1),
    )


@pytest.mark.asyncio
async def test_waiter_returns_the_session_assigned_after_a_wakeup() -> None:
    repository = InMemorySessionRequestRepository()
    wakeups = Wakeups()
    control = ControlPlane(repository, wakeups)
    request = _request()
    assigned_session_id = UUID(int=12)

    waiter = asyncio.create_task(control.acquire(request))
    await asyncio.sleep(0)
    repository.assign(request.id, assigned_session_id)
    wakeups.wake()

    assert await asyncio.wait_for(waiter, timeout=2) == assigned_session_id


@pytest.mark.asyncio
async def test_expired_and_cancelled_requests_raise_their_meaningful_errors() -> None:
    repository = InMemorySessionRequestRepository()
    control = ControlPlane(repository, Wakeups())
    expired = _request(expires_at=datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(SessionRequestTimedOutException):
        await control.acquire(expired)

    cancelled = _request(request_id=UUID(int=17))
    await repository.enqueue(cancelled)
    await repository.end(cancelled.id, RequestStatus.CANCELLED)
    with pytest.raises(SessionRequestCancelledException):
        await control.acquire(cancelled)


@pytest.mark.asyncio
async def test_requests_are_only_visible_and_cancellable_to_their_owner() -> None:
    repository = InMemorySessionRequestRepository()
    control = ControlPlane(repository, Wakeups())
    request = _request()
    await repository.enqueue(request)

    assert await control.get(request.id, request.owner_id) == request
    with pytest.raises(SessionRequestNotFoundException):
        await control.get(request.id, UUID(int=13))
    with pytest.raises(SessionRequestNotFoundException):
        await control.cancel(request.id, UUID(int=14))

    cancelled = await control.cancel(request.id, request.owner_id)
    assert cancelled.status is RequestStatus.CANCELLED
    assert await control.find(UUID(int=15)) is None


@pytest.mark.asyncio
async def test_cancelling_an_assigned_request_preserves_its_session() -> None:
    repository = InMemorySessionRequestRepository()
    control = ControlPlane(repository, Wakeups())
    request = _request()
    await repository.enqueue(request)
    assigned = replace(request, status=RequestStatus.ASSIGNED, session_id=UUID(int=16))
    repository.requests[request.id] = assigned

    assert await control.cancel(request.id, request.owner_id) == assigned
