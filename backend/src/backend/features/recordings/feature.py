from backend.features.recordings.infrastructure import RecordingProvider
from backend.features.recordings.presentation.errors import API_ERRORS
from backend.features.recordings.presentation.router import recording_router
from backend.shared.feature import Feature

feature = Feature(
    name="recordings",
    routers=(recording_router,),
    providers=(RecordingProvider,),
    api_errors=API_ERRORS,
)
