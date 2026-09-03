from datetime import timedelta
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from control_plane.features.browsers.presentation.errors import (
    BROWSER_NOT_FOUND,
    BROWSER_UNAVAILABLE,
)
from control_plane.features.leases.application.service import LeaseService
from control_plane.features.leases.presentation.errors import LEASE_NOT_FOUND
from control_plane.features.leases.presentation.mapper import to_lease_response
from control_plane.features.leases.presentation.schemas import (
    CreateLeaseRequest,
    LeaseResponse,
)
from control_plane.presentation.api_errors import api_error_responses

lease_router = APIRouter(route_class=DishkaRoute, tags=["leases"])


@lease_router.post(
    "/leases",
    response_model=LeaseResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_lease",
    responses=api_error_responses(BROWSER_NOT_FOUND, BROWSER_UNAVAILABLE),
)
async def create_lease(
    request: CreateLeaseRequest, service: FromDishka[LeaseService]
) -> LeaseResponse:
    lease = await service.create(
        browser_id=request.browser_id,
        owner_id=request.owner_id,
        ttl=timedelta(seconds=request.ttl_seconds),
    )
    return to_lease_response(lease)


@lease_router.get(
    "/leases/{lease_id}",
    response_model=LeaseResponse,
    operation_id="get_lease",
    responses=api_error_responses(LEASE_NOT_FOUND),
)
async def get_lease(lease_id: UUID, service: FromDishka[LeaseService]) -> LeaseResponse:
    lease = await service.get(lease_id)
    return to_lease_response(lease)


@lease_router.delete(
    "/leases/{lease_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="release_lease",
    responses=api_error_responses(LEASE_NOT_FOUND),
)
async def release_lease(lease_id: UUID, service: FromDishka[LeaseService]) -> None:
    await service.release(lease_id)
