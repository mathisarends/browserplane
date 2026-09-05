from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from backend.features.health.application.service import HealthService
from backend.features.health.presentation.mapper import to_health_response

health_router = APIRouter(tags=["health"], route_class=DishkaRoute)


@health_router.get("/health", operation_id="health")
async def health(service: FromDishka[HealthService]) -> dict[str, str]:
    return to_health_response(service.liveness())


@health_router.get("/readiness", operation_id="readiness")
async def readiness(service: FromDishka[HealthService]) -> dict[str, str]:
    return to_health_response(await service.readiness())
