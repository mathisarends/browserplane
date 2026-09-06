from browser_worker.features.downloads.infrastructure import DownloadProvider
from browser_worker.features.downloads.presentation.errors import API_ERRORS
from browser_worker.features.downloads.presentation.router import download_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name="downloads",
    routers=(download_router,),
    providers=(DownloadProvider,),
    api_errors=API_ERRORS,
)
