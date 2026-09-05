from backend.features.health.application.models import Health


def to_health_response(health: Health) -> dict[str, str]:
    return {"status": health.status.value}
