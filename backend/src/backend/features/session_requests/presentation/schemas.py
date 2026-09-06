from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.features.browser_requests.domain import RequestStatus


class BrowserRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    status: RequestStatus
    created_at: datetime
    expires_at: datetime
    lease_id: UUID | None
    test_run_id: UUID | None
