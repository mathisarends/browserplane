from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status
from fastapi.responses import FileResponse

from data_plane.features.browsers.presentation.errors import BROWSER_NOT_FOUND
from data_plane.features.downloads.application.service import DownloadService
from data_plane.features.downloads.presentation.errors import DOWNLOAD_NOT_FOUND
from data_plane.features.downloads.presentation.mapper import to_download_response
from data_plane.features.downloads.presentation.schemas import DownloadResponse
from data_plane.presentation.api_errors import api_error_responses

download_router = APIRouter(tags=["downloads"], route_class=DishkaRoute)


@download_router.get(
    "/browser/{browser_id}/downloads",
    operation_id="list_downloads",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def list_downloads(
    browser_id: UUID,
    response: Response,
    service: FromDishka[DownloadService],
) -> list[DownloadResponse]:
    response.headers["Cache-Control"] = "no-store"
    return [to_download_response(item) for item in service.list(browser_id)]


@download_router.delete(
    "/browser/{browser_id}/downloads",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="clear_downloads",
    responses=api_error_responses(BROWSER_NOT_FOUND),
)
async def clear_downloads(
    browser_id: UUID,
    service: FromDishka[DownloadService],
) -> Response:
    await service.clear(browser_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@download_router.get(
    "/browser/{browser_id}/downloads/{download_id}/file",
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
    browser_id: UUID,
    download_id: str,
    service: FromDishka[DownloadService],
) -> FileResponse:
    download = service.file(browser_id, download_id)
    return FileResponse(
        download.path,
        media_type="application/octet-stream",
        filename=download.filename,
    )
