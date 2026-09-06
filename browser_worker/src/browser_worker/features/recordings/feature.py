from browser_worker.features.recordings.infrastructure import RecordingProvider
from browser_worker.features.recordings.presentation.errors import API_ERRORS
from browser_worker.features.recordings.presentation.router import recording_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name='recordings',
    routers=(recording_router,),
    providers=(RecordingProvider,),
    api_errors=API_ERRORS,
)
