from pydantic import BaseModel

from data_plane.features.browsers.application.models import BrowserState


class CreateBrowserRequest(BaseModel):
    id: str


class BrowserResponse(BaseModel):
    id: str
    state: BrowserState
    cdp_url: str


class CapacityResponse(BaseModel):
    total: int
    available: int
