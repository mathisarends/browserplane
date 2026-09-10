from fastapi_canon import Feature

from browser_worker.features.downloads.infrastructure import DownloadProvider
from browser_worker.features.downloads.presentation.errors import ERRORS
from browser_worker.features.downloads.presentation.router import download_router

feature = Feature(
    name="downloads",
    routers=(download_router,),
    providers=(DownloadProvider,),
    errors=ERRORS,
)
