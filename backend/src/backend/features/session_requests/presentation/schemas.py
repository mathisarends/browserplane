from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.features.session_requests.domain import RequestStatus


class SessionRequestResponse(BaseModel):
    """What a queued request looks like from outside, before it holds a session."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    status: RequestStatus
    created_at: datetime
    expires_at: datetime
    session_id: UUID | None
    test_run_id: UUID | None
