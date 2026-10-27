from fastapi_rpckit import RpcService, ServerVariable

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

service = RpcService(version=2)
BROWSER_ENDPOINT = service.socket(
    "/api/v1/sessions/{sessionId}/tunnel",
    name="backendSession",
    channels=(BROWSER_CHANNEL,),
)
BROWSER_CONTRACT = service.contract(
    title="Browser Backend",
    base_url="ws://127.0.0.1:8000",
    variables={"sessionId": ServerVariable(default="{sessionId}")},
)

__all__ = [
    "BROWSER_CHANNEL",
    "BROWSER_CONTRACT",
    "BROWSER_ENDPOINT",
    "BrowserCursorEvent",
    "BrowserEvent",
    "BrowserNavigationEvent",
    "BrowserTabsEvent",
    "BrowserTargetCrashedEvent",
    "BrowserTargetDetachedEvent",
    "events",
    "methods",
    "service",
    "tabs_result",
]
