from uuid import UUID

from browser_worker.features.browser.presentation.schemas import BrowserResponse


def to_browser_response(browser_id: UUID, public_base_url: str) -> BrowserResponse:
    return BrowserResponse(
        id=browser_id,
        cdp_url=(f"{public_base_url.rstrip('/')}/api/v1/browser/{browser_id}/cdp"),
    )
