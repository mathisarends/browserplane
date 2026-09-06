from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from backend.features.browsers.domain.models import BrowserState


class BrowserLeaseSummary(BaseModel):
    """Who is holding a browser, without any of what they are doing on it."""

    session_id: UUID
    owner_id: UUID
    created_at: datetime
    expires_at: datetime
    reclaim_after: datetime
    generation: int


class PooledBrowserResponse(BaseModel):
    """A pool slot as an operator sees it.

    The worker's address stays out: the browser id is the only handle the
    frontend ever needs, and the same rule that keeps sessions from learning
    where a worker lives applies to the admin view.
    """

    id: UUID
    state: BrowserState
    created_at: datetime
    generation: int
    lease: BrowserLeaseSummary | None = None
