from data_plane.application.models import Browser, Capacity
from data_plane.presentation.schemas import BrowserResponse, CapacityResponse


def to_browser_response(browser: Browser) -> BrowserResponse:
    return BrowserResponse(
        id=browser.id,
        state=browser.state,
        cdp_url=browser.cdp_url,
    )


def to_capacity_response(capacity: Capacity) -> CapacityResponse:
    return CapacityResponse(total=capacity.total, available=capacity.available)
