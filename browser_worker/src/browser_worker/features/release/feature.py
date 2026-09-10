from fastapi_canon import Feature

from browser_worker.features.release.infrastructure import ReleaseProvider
from browser_worker.features.release.presentation.errors import ERRORS
from browser_worker.features.release.presentation.router import release_router

feature = Feature(
    name="release",
    routers=(release_router,),
    providers=(ReleaseProvider,),
    errors=ERRORS,
)
