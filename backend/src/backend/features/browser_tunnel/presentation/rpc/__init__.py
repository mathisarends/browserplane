from . import events, methods
from .channel import channel as BROWSER_CHANNEL
from .models import (
    BrowserCursorEvent,
    BrowserEvent,
    BrowserNavigationEvent,
    BrowserTabsEvent,
    BrowserTargetCrashedEvent,
    BrowserTargetDetachedEvent,
    tabs_result,
)

__all__ = [
    "BROWSER_CHANNEL",
    "BrowserCursorEvent",
    "BrowserEvent",
    "BrowserNavigationEvent",
    "BrowserTabsEvent",
    "BrowserTargetCrashedEvent",
    "BrowserTargetDetachedEvent",
    "events",
    "methods",
    "tabs_result",
]
