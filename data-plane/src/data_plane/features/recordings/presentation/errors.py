from typing import Literal

from fastapi import status

from data_plane.features.recordings.application.exceptions import (
    RecordingAlreadyRunningException,
    RecordingFailedException,
    RecordingHasSegmentsException,
    RecordingNotCompletedException,
    RecordingNotFoundException,
    RecordingNotRunningException,
)
from data_plane.presentation.api_errors import ApiErrorSpec
from data_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


class RecordingNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_FOUND]


class RecordingAlreadyRunningError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_ALREADY_RUNNING]


class RecordingNotRunningError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_RUNNING]


class RecordingNotCompletedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_COMPLETED]


class RecordingHasSegmentsError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_HAS_SEGMENTS]


class RecordingFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_FAILED]


RECORDING_NOT_FOUND = ApiErrorSpec(
    exceptions=(RecordingNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.RECORDING_NOT_FOUND,
    response_model=RecordingNotFoundError,
    description="Recording not found",
)
RECORDING_ALREADY_RUNNING = ApiErrorSpec(
    exceptions=(RecordingAlreadyRunningException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.RECORDING_ALREADY_RUNNING,
    response_model=RecordingAlreadyRunningError,
    description="Browser is already being recorded",
)
RECORDING_NOT_RUNNING = ApiErrorSpec(
    exceptions=(RecordingNotRunningException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.RECORDING_NOT_RUNNING,
    response_model=RecordingNotRunningError,
    description="Recording has already been stopped",
)
RECORDING_NOT_COMPLETED = ApiErrorSpec(
    exceptions=(RecordingNotCompletedException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.RECORDING_NOT_COMPLETED,
    response_model=RecordingNotCompletedError,
    description="Recording has no video available",
)
RECORDING_HAS_SEGMENTS = ApiErrorSpec(
    exceptions=(RecordingHasSegmentsException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.RECORDING_HAS_SEGMENTS,
    response_model=RecordingHasSegmentsError,
    description="Recording spans several tabs; download its segments instead",
)
RECORDING_FAILED = ApiErrorSpec(
    exceptions=(RecordingFailedException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.RECORDING_FAILED,
    response_model=RecordingFailedError,
    description="Screen recording failed",
)

API_ERRORS = (
    RECORDING_NOT_FOUND,
    RECORDING_ALREADY_RUNNING,
    RECORDING_NOT_RUNNING,
    RECORDING_NOT_COMPLETED,
    RECORDING_HAS_SEGMENTS,
    RECORDING_FAILED,
)
