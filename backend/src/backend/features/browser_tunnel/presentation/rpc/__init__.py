from pyrpckit import RpcChannel, RpcContract, ServerVariable

from .events import browser_events
from .methods import (
    BROWSER_RPC_MODULES,
)
from .models import (
    BrowserCursorEvent,
    BrowserEvent,
    BrowserNavigationEvent,
    BrowserTabsEvent,
    BrowserTargetCrashedEvent,
    BrowserTargetDetachedEvent,
    tabs_result,
)

BROWSER_CHANNEL = RpcChannel(name="backend-session", version=2)
for module in (*BROWSER_RPC_MODULES, browser_events):
    BROWSER_CHANNEL.include(module)

BROWSER_CONTRACT = RpcContract.from_channels(
    channels=(BROWSER_CHANNEL,),
    title="Browser Backend",
    server_urls={
        "backend-session": "/api/v1/sessions/{sessionId}/tunnel",
    },
    variables={
        "sessionId": ServerVariable(default="{sessionId}"),
    },
)

__all__ = [
    "BROWSER_CHANNEL",
    "BROWSER_CONTRACT",
    "BrowserCursorEvent",
    "BrowserEvent",
    "BrowserNavigationEvent",
    "BrowserTabsEvent",
    "BrowserTargetCrashedEvent",
    "BrowserTargetDetachedEvent",
    "tabs_result",
]
