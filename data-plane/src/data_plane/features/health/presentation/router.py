from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from data_plane.features.health.application.service import HealthService
from data_plane.features.health.presentation.mapper import to_health_response
from data_plane.features.health.presentation.schemas import HealthResponse

health_router = APIRouter(tags=["health"], route_class=DishkaRoute)


@health_router.get("/health", operation_id="health")
async def health(service: FromDishka[HealthService]) -> HealthResponse:
    liveness = service.liveness()
    return to_health_response(liveness)


@health_router.get("/readiness", operation_id="readiness")
async def readiness(service: FromDishka[HealthService]) -> HealthResponse:
    readiness = service.readiness()
    return to_health_response(readiness)
