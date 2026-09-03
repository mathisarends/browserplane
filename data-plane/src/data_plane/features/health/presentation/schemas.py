from pydantic import BaseModel

from data_plane.features.health.application.models import HealthStatus


class HealthResponse(BaseModel):
    status: HealthStatus
