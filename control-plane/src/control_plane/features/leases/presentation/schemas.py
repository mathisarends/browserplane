from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateLeaseRequest(BaseModel):
    browser_id: UUID
    owner_id: UUID
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)


class LeaseResponse(BaseModel):
    id: UUID
    browser_id: UUID
    owner_id: UUID
    expires_at: datetime
    created_at: datetime
