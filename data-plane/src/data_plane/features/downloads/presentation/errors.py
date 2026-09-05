from typing import Literal

from fastapi import status

from data_plane.features.downloads.application.exceptions import (
    DownloadNotFoundException,
)
from data_plane.presentation.api_errors import ApiErrorSpec
from data_plane.presentation.errors import ApiErrorCode, ApiErrorResponse


class DownloadNotFoundError(ApiErrorResponse):
    code: Literal[ApiErrorCode.DOWNLOAD_NOT_FOUND]


DOWNLOAD_NOT_FOUND = ApiErrorSpec(
    exceptions=(DownloadNotFoundException,),
    status_code=status.HTTP_404_NOT_FOUND,
    code=ApiErrorCode.DOWNLOAD_NOT_FOUND,
    response_model=DownloadNotFoundError,
    description="Download not found",
)

API_ERRORS = (DOWNLOAD_NOT_FOUND,)
