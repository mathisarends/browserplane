from fastapi_rpckit import Inject

from backend.features.browser_tunnel.domain import Browser
from backend.features.browser_tunnel.presentation.rpc.channel import channel
from backend.features.browser_tunnel.presentation.rpc.models import (
    ClipboardResult,
    TextParams,
)


@channel.method("browser.clipboard.copy")
async def copy(browser: Inject[Browser]) -> ClipboardResult:
    text = await browser.clipboard.copy()
    return ClipboardResult(text=text)


@channel.method("browser.clipboard.read", idempotent=True)
async def read(browser: Inject[Browser]) -> ClipboardResult:
    text = await browser.clipboard.read()
    return ClipboardResult(text=text)


@channel.method("browser.clipboard.write")
async def write(params: TextParams, browser: Inject[Browser]) -> None:
    await browser.clipboard.write(params.text)
