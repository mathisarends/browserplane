from uuid import UUID

from pydantic import BaseModel


class CreateBrowserRequest(BaseModel):
    id: UUID


class BrowserResponse(BaseModel):
    id: UUID
    cdp_url: str


class CapacityResponse(BaseModel):
    total: int
    available: int
