from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.features.sessions.domain.models import SessionStatus


class OpenSessionRequest(BaseModel):
    owner_id: UUID
    ttl_seconds: int | None = Field(default=None, deprecated=True, exclude=True)
    authentication_profile_id: UUID | None = None
    browser_checkpoint_id: UUID | None = None


class ResumeSessionRequest(BaseModel):
    ttl_seconds: int | None = Field(default=None, deprecated=True, exclude=True)


class CreateBrowserCheckpointRequest(BaseModel):
    authentication_profile_id: UUID | None = None


class BrowserCheckpointResponse(BaseModel):
    id: UUID
    created_at: datetime
    authentication_profile_id: UUID | None


class MountBrowserCheckpointRequest(BaseModel):
    browser_checkpoint_id: UUID


class CreateAuthenticationProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class UpdateAuthenticationProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MountAuthenticationProfileRequest(BaseModel):
    authentication_profile_id: UUID


class AuthenticationProfileResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


class SessionResponse(BaseModel):
    """A session plus the backend paths that carry its live traffic.

    The paths are backend-relative on purpose: the frontend never learns the
    address of a browser worker. A suspended session holds
    no browser, so it has neither a browser id nor live paths until it is
    resumed; ``expires_at`` then says how long it can still be picked up.
    """

    id: UUID
    status: SessionStatus
    owner_id: UUID
    expires_at: datetime | None
    created_at: datetime
    browser_id: UUID | None = None
    tunnel_path: str | None = None
    screencast_path: str | None = None
    browser_checkpoint_id: UUID | None = None
    lease_generation: int | None = None
    reclaim_after: datetime | None = None


class OpenSessionResponse(SessionResponse):
    """A newly leased session and the capacity left after taking its browser."""

    remaining_capacity: int = Field(ge=0)


class OwnerSessionsResponse(BaseModel):
    """Everything one client owns, plus whether the pool has room for one more.

    A page that just loaded needs both answers at once: which sessions to pick
    back up, and whether another browser can still be leased.
    """

    sessions: list[SessionResponse]
    remaining_capacity: int = Field(ge=0)
