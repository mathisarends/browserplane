from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import status
from fastapi_canon import CanonResponse, CanonRouter, ErrorRegistry
from pydantic import BaseModel

from browser_worker.features.browser.presentation.errors import BROWSER_ALREADY_RUNNING
from browser_worker.features.release.application import (
    WorkerReleaseService,
    WorkerRestartService,
)
from browser_worker.features.release.presentation.errors import WORKER_NOT_SUPERVISED

_ROUTE_ERRORS = ErrorRegistry(
    name="release-routes",
    errors=(WORKER_NOT_SUPERVISED, BROWSER_ALREADY_RUNNING),
)

release_router = CanonRouter(
    tags=["worker"], route_class=DishkaRoute, error_registry=_ROUTE_ERRORS
)


class ReleaseWorkerRequest(BaseModel):
    generation: int


class RestartWorkerResponse(BaseModel):
    """The instance that is going away, so its replacement is recognisable."""

    instance_id: UUID


@release_router.post(
    "/release",
    response=CanonResponse.empty(),
    operation_id="release_worker",
    raises=(BROWSER_ALREADY_RUNNING,),
)
async def release_worker(
    request: ReleaseWorkerRequest,
    service: FromDishka[WorkerReleaseService],
) -> None:
    await service.release(request.generation)


@release_router.post(
    "/restart",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="restart_worker",
    raises=(WORKER_NOT_SUPERVISED,),
)
async def restart_worker(
    service: FromDishka[WorkerRestartService],
) -> RestartWorkerResponse:
    retiring = service.restart()
    return RestartWorkerResponse(instance_id=retiring)
