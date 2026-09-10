from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import Response
from fastapi.responses import FileResponse
from fastapi_canon import CanonResponse, CanonRouter

from browser_worker.features.browser.presentation.errors import BROWSER_NOT_FOUND
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.downloads.presentation.errors import DOWNLOAD_NOT_FOUND
from browser_worker.features.downloads.presentation.schemas import DownloadResponse
from browser_worker.presentation.api_files import OCTET_STREAM
from browser_worker.presentation.error_registry import API_ERRORS

download_router = CanonRouter(
    tags=["downloads"],
    route_class=DishkaRoute,
    error_registry=API_ERRORS,
    raises=(BROWSER_NOT_FOUND,),
)


@download_router.get(
    "/browser/downloads",
    operation_id="list_downloads",
)
async def list_downloads(
    response: Response,
    service: FromDishka[DownloadService],
) -> list[DownloadResponse]:
    response.headers["Cache-Control"] = "no-store"
    return [DownloadResponse.model_validate(download) for download in service.list()]


@download_router.delete(
    "/browser/downloads",
    response=CanonResponse.empty(),
    operation_id="clear_downloads",
)
async def clear_downloads(
    service: FromDishka[DownloadService],
) -> None:
    await service.clear()


@download_router.get(
    "/browser/downloads/{download_id}/file",
    operation_id="download_file",
    response_class=FileResponse,
    response=CanonResponse.binary(
        OCTET_STREAM,
        description="Downloaded file",
    ),
    raises=(DOWNLOAD_NOT_FOUND,),
)
async def download_file(
    download_id: str,
    service: FromDishka[DownloadService],
) -> FileResponse:
    download = service.file(download_id)
    return FileResponse(
        download.path,
        media_type=OCTET_STREAM,
        filename=download.filename,
    )
