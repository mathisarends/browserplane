from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from fastapi.responses import FileResponse

from browser_worker.features.browser.presentation.errors import BROWSER_NOT_FOUND
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.downloads.presentation.errors import DOWNLOAD_NOT_FOUND
from browser_worker.features.downloads.presentation.schemas import DownloadResponse
from browser_worker.presentation.api_errors import api_error_responses

download_router = APIRouter(tags=["downloads"], route_class=DishkaRoute)


@download_router.get(
    "/browser/downloads",
    operation_id="list_downloads",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def list_downloads(
    response: Response,
    service: FromDishka[DownloadService],
) -> list[DownloadResponse]:
    response.headers["Cache-Control"] = "no-store"
    return [
        DownloadResponse.model_validate(download)
        for download in service.list()
    ]


@download_router.delete(
    "/browser/downloads",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="clear_downloads",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def clear_downloads(
    service: FromDishka[DownloadService],
) -> Response:
    await service.clear()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@download_router.get(
    "/browser/downloads/{download_id}/file",
    operation_id="download_file",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            },
            "description": "Downloaded file",
        },
        **api_error_responses(BROWSER_NOT_FOUND, DOWNLOAD_NOT_FOUND),
    },
)
async def download_file(
    download_id: str,
    service: FromDishka[DownloadService],
) -> FileResponse:
    download = service.file(download_id)
    return FileResponse(
        download.path,
        media_type="application/octet-stream",
        filename=download.filename,
    )
