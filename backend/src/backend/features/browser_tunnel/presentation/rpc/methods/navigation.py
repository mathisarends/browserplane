from fastapi_rpckit import Inject

from backend.features.browser_tunnel.application import Browser
from backend.features.browser_tunnel.presentation.rpc.channel import channel
from backend.features.browser_tunnel.presentation.rpc.models import (
    NavigateParams,
    ReloadParams,
)


@channel.method("browser.nav.navigate")
async def navigate(params: NavigateParams, browser: Inject[Browser]) -> None:
    await browser.navigation.navigate(params.url)


@channel.method("browser.nav.back")
async def back(browser: Inject[Browser]) -> None:
    await browser.navigation.back()


@channel.method("browser.nav.forward")
async def forward(browser: Inject[Browser]) -> None:
    await browser.navigation.forward()


@channel.method("browser.nav.reload")
async def reload(params: ReloadParams, browser: Inject[Browser]) -> None:
    await browser.navigation.reload(ignore_cache=params.ignore_cache)


@channel.method("browser.nav.stop")
async def stop(browser: Inject[Browser]) -> None:
    await browser.navigation.stop()
