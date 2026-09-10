from fastapi import status
from fastapi_canon import Error, ErrorRegistry

from browser_worker.features.downloads.application.exceptions import (
    DownloadNotFoundException,
)

DOWNLOAD_NOT_FOUND = Error(
    DownloadNotFoundException,
    status=status.HTTP_404_NOT_FOUND,
    code="download_not_found",
    title="Download not found",
    detail=str,
)

API_ERRORS = (DOWNLOAD_NOT_FOUND,)
ERRORS = ErrorRegistry(name="downloads", errors=API_ERRORS)
