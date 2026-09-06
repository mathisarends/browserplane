from backend.features.browsers.infrastructure import BrowserProvider
from backend.features.browsers.presentation.errors import API_ERRORS
from backend.shared.feature import Feature

feature = Feature(
    name="browsers",
    providers=(BrowserProvider,),
    api_errors=API_ERRORS,
)
