from typing import Literal

from fastapi import status

from browser_worker.features.recordings.application.exceptions import (
    RecordingAlreadyExistsException,
    RecordingFailedException,
    RecordingNotCompletedException,
    RecordingNotFoundException,
    RecordingNotRunningException,
)
from browser_worker.presentation.api_errors import ApiErrorSpec
from browser_worker.presentation.errors import ApiErrorCode, ApiErrorResponse


class RecordingNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_FOUND]


class RecordingAlreadyExistsError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_ALREADY_EXISTS]


class RecordingNotRunningError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_RUNNING]


class RecordingNotCompletedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_COMPLETED]


class RecordingFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_FAILED]


RECORDING_NOT_FOUND = ApiErrorSpec(
    exceptions=(RecordingNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.RECORDING_NOT_FOUND,
    response_model=RecordingNotFoundError,
    description="Recording not found",
)
RECORDING_ALREADY_EXISTS = ApiErrorSpec(
    exceptions=(RecordingAlreadyExistsException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.RECORDING_ALREADY_EXISTS,
    response_model=RecordingAlreadyExistsError,
    description="Browser session already has a recording",
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
RECORDING_FAILED = ApiErrorSpec(
    exceptions=(RecordingFailedException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.RECORDING_FAILED,
    response_model=RecordingFailedError,
    description="Screen recording failed",
)

API_ERRORS = (
    RECORDING_NOT_FOUND,
    RECORDING_ALREADY_EXISTS,
    RECORDING_NOT_RUNNING,
    RECORDING_NOT_COMPLETED,
    RECORDING_FAILED,
)
