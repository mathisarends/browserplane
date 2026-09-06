import asyncio
from contextlib import suppress
from datetime import UTC, datetime
from uuid import UUID

from backend.features.session_requests.application.ports import (
    SessionRequestRepository,
)
from backend.features.session_requests.application.wakeups import Wakeups
from backend.features.session_requests.domain import (
    RequestStatus,
    SessionRequest,
    SessionRequestNotFoundException,
    request_ended,
)


class ControlPlane:
    """Owns the queue a caller waits in until a browser carries their session.

    Nothing here holds a database connection between two repository calls: the
    waiting itself happens on a local future, and every wakeup re-reads the
    authoritative state in its own short transaction.
    """

    def __init__(self, repository: SessionRequestRepository, wakeups: Wakeups):
        self._repository = repository
        self._wakeups = wakeups

    async def acquire(self, request: SessionRequest) -> UUID:
        """Enqueue and wait, answering with the id of the assigned session."""
        try:
            request = await self._repository.enqueue(request)
            while True:
                with self._wakeups.register(request.id) as wakeup:
                    current = await self._repository.get(request.id)
                    if current.status is RequestStatus.ASSIGNED:
                        assert current.session_id is not None
                        return current.session_id
                    if current.status in (
                        RequestStatus.CANCELLED,
                        RequestStatus.EXPIRED,
                    ):
                        raise request_ended(current)
                    remaining = (current.expires_at - datetime.now(UTC)).total_seconds()
                    if remaining <= 0:
                        current = await self._repository.end(
                            request.id, RequestStatus.EXPIRED
                        )
                        if current.status is RequestStatus.ASSIGNED:
                            assert current.session_id is not None
                            return current.session_id
                        raise request_ended(current)
                    with suppress(TimeoutError):
                        await asyncio.wait_for(wakeup, timeout=min(remaining, 5))
        except asyncio.CancelledError:
            # Assignment may already have won. It stays discoverable by request ID
            # and expires under the normal lease policy if never picked up.
            with suppress(SessionRequestNotFoundException):
                await asyncio.shield(
                    self._repository.end(request.id, RequestStatus.CANCELLED)
                )
            raise

    async def find(self, request_id: UUID) -> SessionRequest | None:
        """The request behind an idempotency key, or nothing if it is new."""
        try:
            return await self._repository.get(request_id)
        except SessionRequestNotFoundException:
            return None

    async def get(self, request_id: UUID, owner_id: UUID) -> SessionRequest:
        return await self._owned(request_id, owner_id)

    async def cancel(self, request_id: UUID, owner_id: UUID) -> SessionRequest:
        """Give up a waiting request; an assigned one keeps its session."""
        await self._owned(request_id, owner_id)
        return await self._repository.end(request_id, RequestStatus.CANCELLED)

    async def _owned(self, request_id: UUID, owner_id: UUID) -> SessionRequest:
        request = await self._repository.get(request_id)
        if request.owner_id != owner_id:
            # Someone else's request is not theirs to read or end, and a 403
            # would confirm that this id exists.
            raise SessionRequestNotFoundException()
        return request
