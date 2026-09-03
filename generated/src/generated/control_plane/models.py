# Generated from control_plane-openapi.json. Do not edit manually.

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class BrowserCapacityExhaustedError(BaseModel):
    code: Literal["browser_capacity_exhausted"]
    message: str


class BrowserNotFoundError(BaseModel):
    code: Literal["browser_not_found"]
    message: str


class BrowserState(StrEnum):
    STARTING = "starting"
    READY = "ready"
    LEASED = "leased"
    STOPPING = "stopping"
    FAILED = "failed"


class BrowserResponse(BaseModel):
    id: UUID
    state: BrowserState
    websocket_url: str
    created_at: datetime


class BrowserUnavailableError(BaseModel):
    code: Literal["browser_unavailable"]
    message: str


class CreateLeaseRequest(BaseModel):
    browser_id: UUID
    owner_id: UUID
    ttl_seconds: int = 300


class ValidationError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any | None = None
    ctx: dict[str, Any] | None = None


class HTTPValidationError(BaseModel):
    detail: list[ValidationError] | None = None


class LeaseNotFoundError(BaseModel):
    code: Literal["lease_not_found"]
    message: str


class LeaseResponse(BaseModel):
    id: UUID
    browser_id: UUID
    owner_id: UUID
    expires_at: datetime
    created_at: datetime
