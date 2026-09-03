from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from control_plane.features.browsers.application.models import BrowserState


class BrowserResponse(BaseModel):
    id: UUID
    state: BrowserState
    websocket_url: str
    created_at: datetime
