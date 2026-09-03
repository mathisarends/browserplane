# Generated from data_plane-openapi.json. Do not edit manually.

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class BrowserAlreadyRunningError(BaseModel):
    code: Literal["browser_already_running"]
    message: str


class BrowserNotFoundError(BaseModel):
    code: Literal["browser_not_found"]
    message: str


class BrowserResponse(BaseModel):
    id: UUID
    cdp_url: str


class BrowserStartupFailedError(BaseModel):
    code: Literal["browser_startup_failed"]
    message: str


class CreateBrowserRequest(BaseModel):
    id: UUID


class ValidationError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str
    input: Any | None = None
    ctx: dict[str, Any] | None = None


class HTTPValidationError(BaseModel):
    detail: list[ValidationError] | None = None


class HealthStatus(StrEnum):
    OK = "ok"


class HealthResponse(BaseModel):
    status: HealthStatus
