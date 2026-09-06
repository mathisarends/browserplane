import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from backend.features.browser_requests.domain import (
    BrowserRequest,
    RequestEnded,
    RequestStatus,
)


@dataclass(frozen=True)
class Notification:
    channel: str
    payload: str


class Notifier(ABC):
    @abstractmethod
    async def notify(self, notification: Notification) -> None: ...


class RequestRepository(ABC):
    @abstractmethod
    async def enqueue(self, request: BrowserRequest) -> BrowserRequest: ...

    @abstractmethod
    async def get(self, request_id: UUID) -> BrowserRequest: ...

    @abstractmethod
    async def end(self, request_id: UUID, status: RequestStatus) -> BrowserRequest: ...


class Wakeups:
    """Local hints only; registration always precedes the authoritative read."""

    def __init__(self):
        self._waiters: dict[UUID, set[asyncio.Future]] = defaultdict(set)
        self.dispatch = asyncio.Event()

    @contextmanager
    def register(self, request_id: UUID):
        future = asyncio.get_running_loop().create_future()
        self._waiters[request_id].add(future)
        try:
            yield future
        finally:
            self._waiters[request_id].discard(future)
            if not self._waiters[request_id]:
                del self._waiters[request_id]
            future.cancel()

    def wake(self):
        self.dispatch.set()
        for futures in self._waiters.values():
            for future in futures:
                if not future.done():
                    future.set_result(None)


class ControlPlane:
    def __init__(self, repository: RequestRepository, wakeups: Wakeups):
        self._repository = repository
        self._wakeups = wakeups

    async def acquire_browser(self, request: BrowserRequest) -> UUID:
        try:
            request = await self._repository.enqueue(request)
            while True:
                with self._wakeups.register(request.id) as wakeup:
                    current = await self._repository.get(request.id)
                    if current.status is RequestStatus.ASSIGNED:
                        assert current.lease_id is not None
                        return current.lease_id
                    if current.status in (RequestStatus.CANCELLED, RequestStatus.EXPIRED):
                        raise RequestEnded(current)
                    remaining = (current.expires_at - datetime.now(UTC)).total_seconds()
                    if remaining <= 0:
                        current = await self._repository.end(request.id, RequestStatus.EXPIRED)
                        if current.status is RequestStatus.ASSIGNED:
                            assert current.lease_id is not None
                            return current.lease_id
                        raise RequestEnded(current)
                    with suppress(TimeoutError):
                        await asyncio.wait_for(wakeup, timeout=min(remaining, 5))
        except asyncio.CancelledError:
            # Assignment may already have won. It stays discoverable by request ID
            # and expires under the normal lease policy if never picked up.
            with suppress(LookupError):
                await asyncio.shield(self._repository.end(request.id, RequestStatus.CANCELLED))
            raise
