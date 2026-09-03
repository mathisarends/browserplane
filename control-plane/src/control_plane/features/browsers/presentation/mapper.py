from control_plane.features.browsers.application.models import Browser
from control_plane.features.browsers.presentation.schemas import BrowserResponse


def to_browser_response(browser: Browser) -> BrowserResponse:
    return BrowserResponse(
        id=browser.id,
        state=browser.state,
        cdp_url=f"/api/v1/browsers/{browser.id}/cdp",
        created_at=browser.created_at,
    )


def to_browser_list_response(browsers: list[Browser]) -> list[BrowserResponse]:
    return [to_browser_response(browser) for browser in browsers]
