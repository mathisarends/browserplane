from data_plane.features.browsers.application.models import Browser
from data_plane.features.browsers.presentation.schemas import BrowserResponse


def to_browser_response(browser: Browser) -> BrowserResponse:
    return BrowserResponse(
        id=browser.id,
        cdp_url=browser.cdp_url,
    )
