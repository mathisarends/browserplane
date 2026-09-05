from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.features.sessions.application.models import SessionStatus


class OpenSessionRequest(BaseModel):
    owner_id: UUID
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)


class ResumeSessionRequest(BaseModel):
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)


class SessionResponse(BaseModel):
    """A session plus the backend paths that carry its live traffic.

    The paths are backend-relative on purpose: the frontend never learns the
    address of a browsertunnel or data-plane worker. A suspended session holds
    no browser, so it has neither a browser id nor live paths until it is
    resumed; ``expires_at`` then says how long it can still be picked up.
    """

    id: UUID
    status: SessionStatus
    owner_id: UUID
    expires_at: datetime
    created_at: datetime
    browser_id: UUID | None = None
    tunnel_path: str | None = None
    screencast_path: str | None = None
