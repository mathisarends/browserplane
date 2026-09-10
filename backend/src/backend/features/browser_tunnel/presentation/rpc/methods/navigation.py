from pyrpckit import Inject, RpcModule

from backend.features.browser_tunnel.application import Browser
from backend.features.browser_tunnel.presentation.rpc.models import (
    NavigateParams,
    ReloadParams,
)

navigation = RpcModule(namespace="browser.nav")


@navigation.method()
async def navigate(params: NavigateParams, browser: Inject[Browser]) -> None:
    await browser.navigation.navigate(params.url)


@navigation.method()
async def back(browser: Inject[Browser]) -> None:
    await browser.navigation.back()


@navigation.method()
async def forward(browser: Inject[Browser]) -> None:
    await browser.navigation.forward()


@navigation.method()
async def reload(params: ReloadParams, browser: Inject[Browser]) -> None:
    await browser.navigation.reload(ignore_cache=params.ignore_cache)


@navigation.method()
async def stop(browser: Inject[Browser]) -> None:
    await browser.navigation.stop()
