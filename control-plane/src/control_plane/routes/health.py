from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter

router = APIRouter(route_class=DishkaRoute)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness")
async def readiness() -> dict[str, str]:
    return {"status": "ok"}
