from browser_worker.features.downloads.application.models import Download
from browser_worker.features.downloads.presentation.schemas import DownloadResponse


def to_download_response(download: Download) -> DownloadResponse:
    return DownloadResponse(
        id=download.id,
        filename=download.filename,
        url=download.url,
        size=download.size,
    )
