from uuid import UUID

from pydantic import BaseModel

from browser_worker.features.browser.application.service import RunningBrowser


class CreateBrowserRequest(BaseModel):
    id: UUID
    generation: int = 0


class BrowserResponse(BaseModel):
    id: UUID
    generation: int
    cdp_url: str

    @classmethod
    def from_browser(
        cls, browser: RunningBrowser, public_base_url: str
    ) -> BrowserResponse:
        """Address the browser by the public CDP endpoint clients can reach."""
        base_url = public_base_url.rstrip("/")
        return cls(
            id=browser.browser_id,
            generation=browser.generation,
            cdp_url=f"{base_url}/api/v1/browser/cdp",
        )
