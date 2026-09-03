from data_plane.features.health.application.models import Health
from data_plane.features.health.presentation.schemas import HealthResponse


def to_health_response(health: Health) -> HealthResponse:
    return HealthResponse(status=health.status)
