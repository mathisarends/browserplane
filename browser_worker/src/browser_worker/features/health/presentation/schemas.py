from uuid import UUID

from pydantic import BaseModel

from browser_worker.features.health.application import HealthStatus


class HealthResponse(BaseModel):
    status: HealthStatus
    instance_id: UUID
