from datetime import timedelta
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from control_plane.registry import BrowserNotFoundError
from control_plane.services import (
    BrowserUnavailableError,
    LeaseDescriptor,
    LeaseNotFoundError,
    LeaseService,
)

router = APIRouter(route_class=DishkaRoute)


class CreateLeaseRequest(BaseModel):
    browser_id: UUID
    owner_id: UUID
    ttl_seconds: int = Field(default=300, gt=0, le=86_400)


@router.post(
    "/leases",
    response_model=LeaseDescriptor,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_lease",
)
async def create_lease(
    request: CreateLeaseRequest, service: FromDishka[LeaseService]
) -> LeaseDescriptor:
    try:
        return await service.create(
            request.browser_id, request.owner_id, timedelta(seconds=request.ttl_seconds)
        )
    except BrowserNotFoundError as error:
        raise HTTPException(status_code=404, detail="Browser not found") from error
    except BrowserUnavailableError as error:
        raise HTTPException(
            status_code=409, detail="Browser is already leased"
        ) from error


@router.get(
    "/leases/{lease_id}", response_model=LeaseDescriptor, operation_id="get_lease"
)
async def get_lease(
    lease_id: UUID, service: FromDishka[LeaseService]
) -> LeaseDescriptor:
    try:
        return service.get(lease_id)
    except LeaseNotFoundError as error:
        raise HTTPException(status_code=404, detail="Lease not found") from error


@router.delete(
    "/leases/{lease_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="release_lease",
)
async def release_lease(lease_id: UUID, service: FromDishka[LeaseService]) -> Response:
    try:
        await service.release(lease_id)
    except LeaseNotFoundError as error:
        raise HTTPException(status_code=404, detail="Lease not found") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
