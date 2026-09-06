from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from browser_worker.features.recordings.application.models import RecordingState


class RecordingResponse(BaseModel):
    """A screen recording of the browser, as the API reports it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    state: RecordingState
    started_at: datetime
    stopped_at: datetime | None = None
    size_bytes: int | None = None
