from browser_worker.features.release.infrastructure import ReleaseProvider
from browser_worker.features.release.presentation.router import release_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name="release",
    routers=(release_router,),
    providers=(ReleaseProvider,),
)
