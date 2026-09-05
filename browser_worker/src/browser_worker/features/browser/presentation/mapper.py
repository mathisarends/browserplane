from browser_worker.features.browser.application.models import Browser
from browser_worker.features.browser.presentation.schemas import BrowserResponse


def to_browser_response(browser: Browser, public_base_url: str) -> BrowserResponse:
    return BrowserResponse(
        id=browser.id,
        cdp_url=(f"{public_base_url.rstrip('/')}/api/v1/browser/{browser.id}/cdp"),
    )
