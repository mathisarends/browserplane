from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from backend.features.recordings.application.exceptions import (
    RecordingAlreadyExistsException,
    RecordingNotFoundException,
    RecordingNotRunningException,
    RecordingTransferException,
)

RECORDING_NOT_FOUND = Error(
    RecordingNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="recording_not_found",
    title="Recording not found",
    detail=str,
)
RECORDING_ALREADY_EXISTS = Error(
    RecordingAlreadyExistsException,
    status=status.HTTP_409_CONFLICT,
    code="recording_already_exists",
    title="Browser session already has a recording",
    detail=str,
)
RECORDING_NOT_RUNNING = Error(
    RecordingNotRunningException,
    status=status.HTTP_409_CONFLICT,
    code="recording_not_running",
    title="Recording has already been stopped",
    detail=str,
)
RECORDING_TRANSFER_FAILED = Error(
    RecordingTransferException,
    status=status.HTTP_503_SERVICE_UNAVAILABLE,
    code="recording_transfer_failed",
    title="Recording could not be transferred into storage",
    detail=str,
)

API_ERRORS = (
    RECORDING_NOT_FOUND,
    RECORDING_ALREADY_EXISTS,
    RECORDING_NOT_RUNNING,
    RECORDING_TRANSFER_FAILED,
)
ERRORS = ErrorRegistry(name="recordings", errors=API_ERRORS)
