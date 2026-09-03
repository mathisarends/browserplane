from fastapi import APIRouter

health_router = APIRouter(tags=["health"])


@health_router.get("/health", operation_id="health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@health_router.get("/readiness", operation_id="readiness")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}
