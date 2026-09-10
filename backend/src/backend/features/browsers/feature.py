from fastapi_canon import Feature

from backend.features.browsers.infrastructure import BrowserProvider
from backend.features.browsers.presentation.errors import ERRORS

feature = Feature(
    name="browsers",
    providers=(BrowserProvider,),
    errors=ERRORS,
)
