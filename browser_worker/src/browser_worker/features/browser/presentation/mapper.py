from browser_worker.features.browser.application.service import RunningBrowser
from browser_worker.features.browser.presentation.schemas import BrowserResponse


def to_browser_response(
    browser: RunningBrowser, public_base_url: str
) -> BrowserResponse:
    return BrowserResponse(
        id=browser.browser_id,
        generation=browser.generation,
        cdp_url=(
            f"{public_base_url.rstrip('/')}/api/v1/browser/{browser.browser_id}/cdp"
        ),
    )
