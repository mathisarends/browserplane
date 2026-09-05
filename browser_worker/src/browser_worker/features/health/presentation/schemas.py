from pydantic import BaseModel

from browser_worker.features.health.application.models import HealthStatus


class HealthResponse(BaseModel):
    status: HealthStatus
