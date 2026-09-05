from typing import assert_never

from backend.features.browser_tunnel.application import (
    BrowserEvent as DomainEvent,
)
from backend.features.browser_tunnel.application import (
    CursorChanged,
    NavigationChanged,
    TabsChanged,
    TargetCrashed,
    TargetDetached,
)
from backend.features.browser_tunnel.presentation.rpc.models import (
    BrowserCursorEvent,
    BrowserEvent,
    BrowserNavigationEvent,
    BrowserTabsEvent,
    BrowserTargetCrashedEvent,
    BrowserTargetDetachedEvent,
    tabs_result,
)

BROWSER_EVENT_METHOD = "browser.event"


def browser_event(event: DomainEvent) -> BrowserEvent:
    """Translate a domain browser event into its wire representation."""
    match event:
        case TabsChanged(tabs=tabs):
            return BrowserTabsEvent(tabs=tabs_result(tabs).tabs)
        case NavigationChanged():
            return BrowserNavigationEvent(
                tabId=event.tab_id,
                title=event.title,
                url=event.url,
                loading=event.loading,
                canGoBack=event.can_go_back,
                canGoForward=event.can_go_forward,
                faviconUrl=event.favicon_url,
                error=event.error,
            )
        case CursorChanged():
            return BrowserCursorEvent(tabId=event.tab_id, cursor=event.cursor)
        case TargetCrashed():
            return BrowserTargetCrashedEvent(
                tabId=event.tab_id,
                status=event.status,
                errorCode=event.error_code,
            )
        case TargetDetached():
            return BrowserTargetDetachedEvent(tabId=event.tab_id)
        case _:
            assert_never(event)
