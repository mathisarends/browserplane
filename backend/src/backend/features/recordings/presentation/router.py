from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from backend.features.browsers.presentation.errors import BROWSER_NOT_FOUND
from backend.features.recordings.application.service import RecordingService
from backend.features.recordings.presentation.errors import (
    RECORDING_ALREADY_RUNNING,
    RECORDING_NOT_FOUND,
    RECORDING_NOT_RUNNING,
    RECORDING_TRANSFER_FAILED,
)
from backend.presentation.api_errors import api_error_responses
from generated.browser_worker import RecordingResponse

recording_router = APIRouter(tags=["recordings"], route_class=DishkaRoute)


@recording_router.post(
    "/browser/{browser_id}/recordings",
    status_code=status.HTTP_201_CREATED,
    operation_id="start_recording",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        RECORDING_ALREADY_RUNNING,
        RECORDING_TRANSFER_FAILED,
    ),
)
async def start_recording(
    browser_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    return await service.start(browser_id)


@recording_router.get(
    "/browser/{browser_id}/recordings/{recording_id}",
    operation_id="inspect_recording",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        RECORDING_NOT_FOUND,
        RECORDING_TRANSFER_FAILED,
    ),
)
async def inspect_recording(
    browser_id: UUID,
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    return await service.inspect(browser_id, recording_id)


@recording_router.post(
    "/browser/{browser_id}/recordings/{recording_id}/stop",
    operation_id="stop_recording",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        RECORDING_NOT_FOUND,
        RECORDING_NOT_RUNNING,
        RECORDING_TRANSFER_FAILED,
    ),
)
async def stop_recording(
    browser_id: UUID,
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    return await service.stop(browser_id, recording_id)
