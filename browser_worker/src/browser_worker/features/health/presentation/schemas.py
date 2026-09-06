from uuid import UUID

from pydantic import BaseModel

from browser_worker.features.health.application.models import HealthStatus


class HealthResponse(BaseModel):
    status: HealthStatus
    instance_id: UUID
