from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from backend.features.sessions.application.models import SessionStatus
from generated.data_plane import AuthenticationStateSchema, BrowserStateSchema


class OpenSessionRequest(BaseModel):
    owner_id: UUID
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)
    authentication_state: AuthenticationStateSchema | None = None
    browser_state: BrowserStateSchema | None = None


class ResumeSessionRequest(BaseModel):
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)


class CaptureBrowserStateSnapshotRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_browser: str = Field(min_length=1, max_length=200)


class BrowserStateSnapshotResponse(BaseModel):
    id: UUID
    name: str
    source_browser: str
    created_at: datetime
    browser_state: BrowserStateSchema


class CaptureAuthenticationStateSnapshotRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_browser: str = Field(min_length=1, max_length=200)


class AuthenticationStateSnapshotResponse(BaseModel):
    id: UUID
    name: str
    source_browser: str
    created_at: datetime
    authentication_state: AuthenticationStateSchema


class SessionResponse(BaseModel):
    """A session plus the backend paths that carry its live traffic.

    The paths are backend-relative on purpose: the frontend never learns the
    address of a data-plane worker. A suspended session holds
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


class OpenSessionResponse(SessionResponse):
    """A newly leased session and the capacity left after taking its browser."""

    remaining_capacity: int = Field(ge=0)
