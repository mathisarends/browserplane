from fastapi import APIRouter

from data_plane.presentation.schemas import StatusResponse

health_router = APIRouter(tags=["health"])


@health_router.get("/health", operation_id="health")
async def health() -> StatusResponse:
    return StatusResponse(status="ok")


@health_router.get("/readiness", operation_id="readiness")
async def readiness() -> StatusResponse:
    return StatusResponse(status="ok")
