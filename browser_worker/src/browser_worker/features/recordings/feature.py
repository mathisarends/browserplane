from fastapi_canon import Feature

from browser_worker.features.recordings.infrastructure import RecordingProvider
from browser_worker.features.recordings.presentation.errors import ERRORS
from browser_worker.features.recordings.presentation.router import recording_router

feature = Feature(
    name="recordings",
    routers=(recording_router,),
    providers=(RecordingProvider,),
    errors=ERRORS,
)
