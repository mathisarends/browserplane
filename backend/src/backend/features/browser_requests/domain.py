from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RequestStatus(StrEnum):
    QUEUED = "QUEUED"
    PROVISIONING = "PROVISIONING"
    ASSIGNED = "ASSIGNED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class BrowserRequest:
    id: UUID
    owner_id: UUID
    status: RequestStatus
    created_at: datetime
    expires_at: datetime
    lease_id: UUID | None = None
    test_run_id: UUID | None = None
    authentication_profile_id: UUID | None = None
    browser_checkpoint_id: UUID | None = None
    resume_session_id: UUID | None = None


class RequestConflict(Exception):
    """An idempotency key was reused with different input."""


class RequestEnded(Exception):
    def __init__(self, request: BrowserRequest):
        self.request = request
        super().__init__(f"Browser request {request.status.lower()}")
