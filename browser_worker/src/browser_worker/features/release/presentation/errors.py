from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from browser_worker.features.release.application.exceptions import (
    WorkerNotSupervisedException,
)

WORKER_NOT_SUPERVISED = Error(
    WorkerNotSupervisedException,
    status=status.HTTP_409_CONFLICT,
    code="worker_not_supervised",
    title="Worker has no restart policy",
    detail=str,
)

API_ERRORS = (WORKER_NOT_SUPERVISED,)
ERRORS = ErrorRegistry(name="release", errors=API_ERRORS)
