from fastapi_canon import Feature

from backend.features.recordings.infrastructure import RecordingProvider
from backend.features.recordings.presentation.errors import ERRORS
from backend.features.recordings.presentation.router import recording_router

feature = Feature(
    name="recordings",
    routers=(recording_router,),
    providers=(RecordingProvider,),
    errors=ERRORS,
)
