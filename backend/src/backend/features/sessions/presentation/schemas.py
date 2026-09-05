from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OpenSessionRequest(BaseModel):
    owner_id: UUID
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)


class SessionResponse(BaseModel):
    """A session plus the backend paths that carry its live traffic.

    The paths are backend-relative on purpose: the frontend never learns the
    address of a browsertunnel or data-plane worker.
    """

    id: UUID
    browser_id: UUID
    owner_id: UUID
    expires_at: datetime
    created_at: datetime
    tunnel_path: str
    screencast_path: str
