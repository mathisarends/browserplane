from typing import Literal

from fastapi import status

from browser_worker.features.release.application.exceptions import (
    WorkerNotSupervisedException,
)
from browser_worker.presentation.api_errors import ApiErrorSpec
from browser_worker.presentation.errors import ApiErrorCode, ApiErrorResponse


class WorkerNotSupervisedError(ApiErrorResponse):
    code: Literal[ApiErrorCode.WORKER_NOT_SUPERVISED]


WORKER_NOT_SUPERVISED = ApiErrorSpec(
    exceptions=(WorkerNotSupervisedException,),
    status_code=status.HTTP_409_CONFLICT,
    code=ApiErrorCode.WORKER_NOT_SUPERVISED,
    response_model=WorkerNotSupervisedError,
    description="Worker has no restart policy",
)

API_ERRORS = (WORKER_NOT_SUPERVISED,)
