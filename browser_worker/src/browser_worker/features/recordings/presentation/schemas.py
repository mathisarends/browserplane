from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from browser_worker.features.recordings.application.models import RecordingState


class RecordingResponse(BaseModel):
    id: UUID
    browser_id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    size_bytes: int | None = None
