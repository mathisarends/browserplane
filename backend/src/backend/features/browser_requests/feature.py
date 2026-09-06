from backend.features.browser_requests.infrastructure.provider import RequestProvider
from backend.features.browser_requests.presentation import router
from backend.shared.feature import Feature

feature = Feature(name="browser_requests", providers=(RequestProvider,), routers=(router,))
