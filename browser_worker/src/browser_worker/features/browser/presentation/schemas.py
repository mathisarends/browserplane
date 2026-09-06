from uuid import UUID

from pydantic import BaseModel


class CreateBrowserRequest(BaseModel):
    id: UUID
    generation: int = 0


class BrowserResponse(BaseModel):
    id: UUID
    generation: int
    cdp_url: str
