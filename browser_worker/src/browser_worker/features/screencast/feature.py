from browser_worker.features.screencast.infrastructure import ScreencastProvider
from browser_worker.features.screencast.presentation.router import screencast_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name='screencast',
    routers=(screencast_router,),
    providers=(ScreencastProvider,),
)
