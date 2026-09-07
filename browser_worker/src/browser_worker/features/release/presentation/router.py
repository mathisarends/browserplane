from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from browser_worker.features.release.application.restart import WorkerRestartService
from browser_worker.features.release.application.service import WorkerReleaseService
from browser_worker.features.release.presentation.errors import WORKER_NOT_SUPERVISED
from browser_worker.presentation.api_errors import api_error_responses

release_router = APIRouter(tags=["worker"], route_class=DishkaRoute)


class ReleaseWorkerRequest(BaseModel):
    generation: int


class RestartWorkerResponse(BaseModel):
    """The instance that is going away, so its replacement is recognisable."""

    instance_id: UUID


@release_router.post(
    "/release",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="release_worker",
)
async def release_worker(
    request: ReleaseWorkerRequest,
    service: FromDishka[WorkerReleaseService],
) -> Response:
    await service.release(request.generation)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@release_router.post(
    "/restart",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="restart_worker",
    responses=api_error_responses(WORKER_NOT_SUPERVISED),
)
async def restart_worker(
    service: FromDishka[WorkerRestartService],
) -> RestartWorkerResponse:
    retiring = service.restart()
    return RestartWorkerResponse(instance_id=retiring)
