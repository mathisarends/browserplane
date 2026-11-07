from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import Response, status
from fastapi_canon import CanonResponse, CanonRouter, ErrorRegistry

from backend.features.browsers.presentation.errors import BROWSER_NOT_FOUND
from backend.features.recordings.application import RecordingService
from backend.features.recordings.presentation.errors import (
    RECORDING_ALREADY_EXISTS,
    RECORDING_NOT_FOUND,
    RECORDING_NOT_RUNNING,
    RECORDING_TRANSFER_FAILED,
)
from backend.features.recordings.presentation.mapper import to_recording_response
from backend.features.recordings.presentation.schemas import RecordingResponse

_ROUTE_ERRORS = ErrorRegistry(
    name="recordings-routes",
    errors=(
        BROWSER_NOT_FOUND,
        RECORDING_TRANSFER_FAILED,
        RECORDING_ALREADY_EXISTS,
        RECORDING_NOT_FOUND,
        RECORDING_NOT_RUNNING,
    ),
)

recording_router = CanonRouter(
    tags=["recordings"],
    route_class=DishkaRoute,
    error_registry=_ROUTE_ERRORS,
    raises=(BROWSER_NOT_FOUND, RECORDING_TRANSFER_FAILED),
)


@recording_router.post(
    "/browser/{browser_id}/recordings",
    status_code=status.HTTP_201_CREATED,
    operation_id="start_recording",
    raises=(RECORDING_ALREADY_EXISTS,),
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
    raises=(RECORDING_NOT_FOUND, RECORDING_NOT_RUNNING),
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
    response=CanonResponse.binary("video/mp4", description="Completed MP4 recording"),
    raises=(RECORDING_NOT_FOUND,),
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
