from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from browser_worker.features.release.application.service import WorkerReleaseService

release_router = APIRouter(tags=["worker"], route_class=DishkaRoute)


@release_router.post(
    "/release",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="release_worker",
)
async def release_worker(service: FromDishka[WorkerReleaseService]) -> Response:
    await service.release()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
