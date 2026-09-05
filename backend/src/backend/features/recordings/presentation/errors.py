from typing import Literal

from fastapi import status

from backend.features.recordings.application.exceptions import (
    RecordingAlreadyRunningException,
    RecordingNotFoundException,
    RecordingNotRunningException,
    RecordingTransferException,
)
from backend.presentation.api_errors import ApiErrorSpec
from backend.presentation.errors import ApiErrorCode, ApiErrorResponse


class RecordingNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_FOUND]


class RecordingAlreadyRunningError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_ALREADY_RUNNING]


class RecordingNotRunningError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_NOT_RUNNING]


class RecordingTransferFailedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.RECORDING_TRANSFER_FAILED]


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
RECORDING_TRANSFER_FAILED = ApiErrorSpec(
    exceptions=(RecordingTransferException,),
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    code=ApiErrorCode.RECORDING_TRANSFER_FAILED,
    response_model=RecordingTransferFailedError,
    description="Recording could not be transferred into storage",
)

API_ERRORS = (
    RECORDING_NOT_FOUND,
    RECORDING_ALREADY_RUNNING,
    RECORDING_NOT_RUNNING,
    RECORDING_TRANSFER_FAILED,
)
