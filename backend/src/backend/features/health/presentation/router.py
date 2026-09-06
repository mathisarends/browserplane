from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from backend.features.health.application.models import Health
from backend.features.health.application.service import HealthService

health_router = APIRouter(tags=["health"], route_class=DishkaRoute)


@health_router.get("/health", operation_id="health")
async def health(service: FromDishka[HealthService]) -> Health:
    return service.liveness()


@health_router.get("/readiness", operation_id="readiness")
async def readiness(service: FromDishka[HealthService]) -> Health:
    return await service.readiness()
