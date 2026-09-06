from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.exceptions import BackendException


class RequestStatus(StrEnum):
    QUEUED = "QUEUED"
    PROVISIONING = "PROVISIONING"
    ASSIGNED = "ASSIGNED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class SessionRequest:
    """One caller's claim on a session that has no browser yet.

    An assignment mints the lease and the session aggregate under the same id,
    so ``session_id`` is what the caller was waiting for all along.
    """

    id: UUID
    owner_id: UUID
    status: RequestStatus
    created_at: datetime
    expires_at: datetime
    session_id: UUID | None = None
    test_run_id: UUID | None = None
    authentication_profile_id: UUID | None = None
    browser_checkpoint_id: UUID | None = None
    resume_session_id: UUID | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            RequestStatus.ASSIGNED,
            RequestStatus.CANCELLED,
            RequestStatus.EXPIRED,
        )


class SessionRequestNotFoundException(BackendException):
    message = "Session request not found"


class SessionRequestConflictException(BackendException):
    """A request id was reused with different input."""

    message = "Request ID already belongs to different input"


class SessionRequestEndedException(BackendException):
    """The request reached a terminal state without becoming a session."""

    def __init__(self, request: SessionRequest) -> None:
        super().__init__(details={"request_id": request.id})
        self.request = request


class SessionRequestTimedOutException(SessionRequestEndedException):
    message = "Session request timed out before a browser became available"


class SessionRequestCancelledException(SessionRequestEndedException):
    message = "Session request was cancelled"


def request_ended(request: SessionRequest) -> SessionRequestEndedException:
    """The terminal state a waiter ran into, as the failure it means to them."""
    if request.status is RequestStatus.EXPIRED:
        return SessionRequestTimedOutException(request)
    return SessionRequestCancelledException(request)
