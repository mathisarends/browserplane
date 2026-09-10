from fastapi_canon import Feature

from browser_worker.features.screencast.infrastructure import ScreencastProvider
from browser_worker.features.screencast.presentation.router import screencast_router

feature = Feature(
    name="screencast",
    routers=(screencast_router,),
    providers=(ScreencastProvider,),
)
