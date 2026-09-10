from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from browser_worker.features.browser.presentation.errors import BROWSER_NOT_FOUND
from browser_worker.features.recordings.application.models import RecordingFormat
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.recordings.presentation.errors import (
    RECORDING_ALREADY_EXISTS,
    RECORDING_FAILED,
    RECORDING_NOT_COMPLETED,
    RECORDING_NOT_FOUND,
    RECORDING_NOT_RUNNING,
)
from browser_worker.features.recordings.presentation.schemas import RecordingResponse
from browser_worker.presentation.api_files import api_file_response
from browser_worker.presentation.error_registry import API_ERRORS

recording_router = APIRouter(tags=["recordings"], route_class=DishkaRoute)


@recording_router.post(
    "/browser/recordings",
    status_code=status.HTTP_201_CREATED,
    operation_id="start_recording",
    responses=API_ERRORS.responses(
        BROWSER_NOT_FOUND,
        RECORDING_ALREADY_EXISTS,
        RECORDING_FAILED,
    ),
)
async def start_recording(
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    recording = await service.start()
    return RecordingResponse.model_validate(recording)


@recording_router.post(
    "/browser/recordings/{recording_id}/stop",
    operation_id="stop_recording",
    responses=API_ERRORS.responses(
        RECORDING_NOT_FOUND,
        RECORDING_NOT_RUNNING,
        RECORDING_FAILED,
    ),
)
async def stop_recording(
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    recording = await service.stop(recording_id)
    return RecordingResponse.model_validate(recording)


@recording_router.get(
    "/browser/recordings/{recording_id}/file",
    operation_id="download_recording",
    response_class=FileResponse,
    responses=api_file_response(
        "Recorded video",
        API_ERRORS.responses(RECORDING_NOT_FOUND, RECORDING_NOT_COMPLETED),
        media_types=RecordingFormat.media_types(),
    ),
)
async def download_recording(
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> FileResponse:
    video = service.file(recording_id)
    return FileResponse(
        video.path,
        media_type=video.media_type,
        filename=video.filename,
    )
