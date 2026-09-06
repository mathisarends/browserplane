from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from browser_worker.features.health.application.service import HealthService
from browser_worker.features.health.presentation.schemas import HealthResponse

health_router = APIRouter(tags=["health"], route_class=DishkaRoute)


@health_router.get("/health", operation_id="health")
async def health(service: FromDishka[HealthService]) -> HealthResponse:
    status = service.liveness()
    return HealthResponse(status=status, instance_id=service.instance_id)


@health_router.get("/readiness", operation_id="readiness")
async def readiness(service: FromDishka[HealthService]) -> HealthResponse:
    status = service.readiness()
    return HealthResponse(status=status, instance_id=service.instance_id)
