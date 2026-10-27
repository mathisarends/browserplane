from fastapi_rpckit import Inject, RpcError

from backend.features.browser_tunnel.application import (
    Browser,
    BrowserTabNotFoundError,
)
from backend.features.browser_tunnel.presentation.rpc.channel import channel
from backend.features.browser_tunnel.presentation.rpc.models import (
    CreateTabParams,
    TabParams,
    TabsResult,
    tabs_result,
)


class BrowserTabNotFound(RpcError):
    code = "browser_tab_not_found"
    rpc_code = -32004
    message = "Browser tab not found"


@channel.method("browser.tab.list")
async def list_tabs(browser: Inject[Browser]) -> TabsResult:
    result = await browser.tabs.list()
    return tabs_result(result)


@channel.method("browser.tab.create")
async def create(params: CreateTabParams, browser: Inject[Browser]) -> TabsResult:
    result = await browser.tabs.create(params.url)
    return tabs_result(result)


@channel.method("browser.tab.activate", raises=(BrowserTabNotFound,))
async def activate(params: TabParams, browser: Inject[Browser]) -> TabsResult:
    try:
        result = await browser.tabs.activate(params.tab_id)
    except BrowserTabNotFoundError as error:
        raise BrowserTabNotFound(
            message=f"Browser tab not found: {params.tab_id}"
        ) from error
    return tabs_result(result)


@channel.method("browser.tab.close", raises=(BrowserTabNotFound,))
async def close(params: TabParams, browser: Inject[Browser]) -> TabsResult:
    try:
        result = await browser.tabs.close(params.tab_id)
    except BrowserTabNotFoundError as error:
        raise BrowserTabNotFound(
            message=f"Browser tab not found: {params.tab_id}"
        ) from error
    return tabs_result(result)
