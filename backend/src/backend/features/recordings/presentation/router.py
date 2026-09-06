from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from backend.features.browsers.presentation.errors import BROWSER_NOT_FOUND
from backend.features.recordings.application.service import RecordingService
from backend.features.recordings.presentation.errors import (
    RECORDING_ALREADY_EXISTS,
    RECORDING_NOT_FOUND,
    RECORDING_NOT_RUNNING,
    RECORDING_TRANSFER_FAILED,
)
from backend.features.recordings.presentation.mapper import to_recording_response
from backend.features.recordings.presentation.schemas import RecordingResponse
from backend.presentation.api_errors import api_error_responses

recording_router = APIRouter(tags=["recordings"], route_class=DishkaRoute)


@recording_router.post(
    "/browser/{browser_id}/recordings",
    status_code=status.HTTP_201_CREATED,
    operation_id="start_recording",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        RECORDING_ALREADY_EXISTS,
        RECORDING_TRANSFER_FAILED,
    ),
)
async def start_recording(
    browser_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    recording = await service.start(browser_id)
    return to_recording_response(recording)


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
    recording = await service.inspect(browser_id, recording_id)
    return to_recording_response(recording)


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
    recording = await service.stop(browser_id, recording_id)
    return to_recording_response(recording)


@recording_router.get(
    "/browser/{browser_id}/recordings/{recording_id}/file",
    operation_id="download_recording",
    responses={
        200: {
            "content": {
                "video/mp4": {"schema": {"type": "string", "format": "binary"}}
            },
            "description": "Completed MP4 recording",
        },
        **api_error_responses(
            BROWSER_NOT_FOUND,
            RECORDING_NOT_FOUND,
            RECORDING_TRANSFER_FAILED,
        ),
    },
)
async def download_recording(
    browser_id: UUID,
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> Response:
    content = await service.file(browser_id, recording_id)
    return Response(
        content=content,
        media_type="video/mp4",
        headers={
            "Content-Disposition": (
                f'attachment; filename="recording-{recording_id}.mp4"'
            )
        },
    )
