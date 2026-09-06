from pydantic import BaseModel

from browser_worker.features.browser.application.service import RunningBrowser


class CreateBrowserRequest(BaseModel):
    generation: int


class BrowserResponse(BaseModel):
    generation: int
    cdp_url: str

    @classmethod
    def from_browser(
        cls, browser: RunningBrowser, public_base_url: str
    ) -> BrowserResponse:
        """Address the browser by the public CDP endpoint clients can reach."""
        base_url = public_base_url.rstrip("/")
        return cls(
            generation=browser.generation,
            cdp_url=f"{base_url}/api/v1/browser/cdp",
        )
