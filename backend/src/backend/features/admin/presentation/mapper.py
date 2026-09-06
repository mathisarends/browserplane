from backend.features.admin.application.models import PooledBrowser
from backend.features.admin.presentation.schemas import (
    BrowserLeaseSummary,
    PooledBrowserResponse,
)
from backend.features.browsers.domain.models import Browser


def to_pooled_browser_response(pooled: PooledBrowser) -> PooledBrowserResponse:
    lease = pooled.lease
    return PooledBrowserResponse(
        id=pooled.browser.id,
        state=pooled.browser.state,
        created_at=pooled.browser.created_at,
        generation=pooled.browser.generation,
        lease=(
            BrowserLeaseSummary(
                session_id=lease.id,
                owner_id=lease.owner_id,
                created_at=lease.created_at,
                expires_at=lease.expires_at,
                reclaim_after=lease.reclaim_after,
                generation=lease.generation,
            )
            if lease is not None
            else None
        ),
    )


def to_browser_response(browser: Browser) -> PooledBrowserResponse:
    """A browser right after it was released or restarted, so never leased."""
    return to_pooled_browser_response(PooledBrowser(browser=browser))
