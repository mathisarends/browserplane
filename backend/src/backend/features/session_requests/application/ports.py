from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from backend.features.session_requests.domain import RequestStatus, SessionRequest


@dataclass(frozen=True)
class Notification:
    channel: str
    payload: str


class Notifier(ABC):
    @abstractmethod
    async def notify(self, notification: Notification) -> None: ...


class SessionRequestRepository(ABC):
    """Each method owns its own short transaction; no state spans two calls."""

    @abstractmethod
    async def enqueue(self, request: SessionRequest) -> SessionRequest: ...

    @abstractmethod
    async def get(self, request_id: UUID) -> SessionRequest: ...

    @abstractmethod
    async def end(self, request_id: UUID, status: RequestStatus) -> SessionRequest: ...
