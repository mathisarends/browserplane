from pyrpckit import Inject, RpcModule

from backend.features.browser_tunnel.application import Browser
from backend.features.browser_tunnel.presentation.rpc.models import (
    ClipboardResult,
    TextParams,
)

clipboard = RpcModule(namespace="browser.clipboard")


@clipboard.method()
async def copy(browser: Inject[Browser]) -> ClipboardResult:
    text = await browser.clipboard.copy()
    return ClipboardResult(text=text)


@clipboard.method()
async def read(browser: Inject[Browser]) -> ClipboardResult:
    text = await browser.clipboard.read()
    return ClipboardResult(text=text)


@clipboard.method()
async def write(params: TextParams, browser: Inject[Browser]) -> None:
    await browser.clipboard.write(params.text)
