from browser_worker.features.browser.infrastructure import BrowserProvider
from browser_worker.features.browser.presentation.errors import API_ERRORS
from browser_worker.features.browser.presentation.router import browser_router
from browser_worker.shared.feature import Feature

feature = Feature(
    name='browser',
    routers=(browser_router,),
    providers=(BrowserProvider,),
    api_errors=API_ERRORS,
)
