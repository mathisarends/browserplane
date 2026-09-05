from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from browser_worker.features.browser.presentation.errors import BROWSER_NOT_FOUND
from browser_worker.features.recordings.application.models import RecordingFile
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.recordings.presentation.errors import (
    RECORDING_ALREADY_RUNNING,
    RECORDING_FAILED,
    RECORDING_HAS_SEGMENTS,
    RECORDING_NOT_COMPLETED,
    RECORDING_NOT_FOUND,
    RECORDING_NOT_RUNNING,
)
from browser_worker.features.recordings.presentation.mapper import to_recording_response
from browser_worker.features.recordings.presentation.schemas import RecordingResponse
from browser_worker.presentation.api_errors import api_error_responses

recording_router = APIRouter(tags=["recordings"], route_class=DishkaRoute)


@recording_router.post(
    "/browser/{browser_id}/recordings",
    status_code=status.HTTP_201_CREATED,
    operation_id="start_recording",
    responses=api_error_responses(
        BROWSER_NOT_FOUND,
        RECORDING_ALREADY_RUNNING,
        RECORDING_FAILED,
    ),
)
async def start_recording(
    browser_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    recording = await service.start(browser_id)
    return to_recording_response(recording)


@recording_router.post(
    "/browser/{browser_id}/recordings/{recording_id}/stop",
    operation_id="stop_recording",
    responses=api_error_responses(
        RECORDING_NOT_FOUND,
        RECORDING_NOT_RUNNING,
        RECORDING_FAILED,
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
    "/browser/{browser_id}/recordings/{recording_id}",
    operation_id="inspect_recording",
    responses=api_error_responses(RECORDING_NOT_FOUND),
)
async def inspect_recording(
    browser_id: UUID,
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> RecordingResponse:
    recording = service.get(browser_id, recording_id)
    return to_recording_response(recording)


@recording_router.get(
    "/browser/{browser_id}/recordings/{recording_id}/file",
    operation_id="download_recording",
    response_class=FileResponse,
    responses=api_error_responses(
        RECORDING_NOT_FOUND,
        RECORDING_NOT_COMPLETED,
        RECORDING_HAS_SEGMENTS,
    ),
)
async def download_recording(
    browser_id: UUID,
    recording_id: UUID,
    service: FromDishka[RecordingService],
) -> FileResponse:
    """Download a recording that stayed on one tab and is therefore one file."""
    video = service.file(browser_id, recording_id)
    return _to_file_response(video)


@recording_router.get(
    "/browser/{browser_id}/recordings/{recording_id}/segments/{index}/file",
    operation_id="download_recording_segment",
    response_class=FileResponse,
    responses=api_error_responses(RECORDING_NOT_FOUND, RECORDING_NOT_COMPLETED),
)
async def download_recording_segment(
    browser_id: UUID,
    recording_id: UUID,
    index: int,
    service: FromDishka[RecordingService],
) -> FileResponse:
    """Download the video of one tab, as listed in the recording's segments."""
    video = service.segment_file(browser_id, recording_id, index)
    return _to_file_response(video)


def _to_file_response(video: RecordingFile) -> FileResponse:
    return FileResponse(
        video.path,
        media_type=video.media_type,
        filename=video.filename,
    )
