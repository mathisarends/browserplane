from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import Response, status
from fastapi_canon import CanonRouter

from backend.features.health.application.models import Health, HealthStatus
from backend.features.health.application.service import HealthService

health_router = CanonRouter(tags=["health"], route_class=DishkaRoute)


@health_router.get("/health", operation_id="health")
async def health(service: FromDishka[HealthService]) -> Health:
    return service.liveness()


@health_router.get("/readiness", operation_id="readiness")
async def readiness(service: FromDishka[HealthService], response: Response) -> Health:
    result = await service.readiness()
    # Probes read the status code, not the body.
    if result.status is not HealthStatus.OK:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
