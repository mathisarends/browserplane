from fastapi_rpckit import Inject

from backend.features.browser_tunnel.application import Browser
from backend.features.browser_tunnel.presentation.rpc.channel import channel
from backend.features.browser_tunnel.presentation.rpc.models import (
    KeyParams,
    MouseParams,
    ScrollParams,
    TextParams,
)


@channel.method("browser.input.mouse")
async def mouse(params: MouseParams, browser: Inject[Browser]) -> None:
    await browser.input.mouse(
        event_type=params.type,
        x=params.x,
        y=params.y,
        button=params.button,
        buttons=params.buttons,
        modifiers=params.modifiers,
        click_count=params.click_count,
    )


@channel.method("browser.input.scroll")
async def scroll(params: ScrollParams, browser: Inject[Browser]) -> None:
    await browser.input.scroll(
        x=params.x,
        y=params.y,
        delta_x=params.delta_x,
        delta_y=params.delta_y,
    )


@channel.method("browser.input.key")
async def key(params: KeyParams, browser: Inject[Browser]) -> None:
    await browser.input.key(
        event_type=params.type,
        key=params.key,
        code=params.code,
        text=params.text,
        unmodified_text=params.unmodified_text,
        modifiers=params.modifiers,
        auto_repeat=params.auto_repeat,
        windows_virtual_key_code=params.windows_virtual_key_code,
        native_virtual_key_code=params.native_virtual_key_code,
        location=params.location,
        is_keypad=params.is_keypad,
        is_system_key=params.is_system_key,
    )


@channel.method("browser.input.text.insert")
async def insert_text(params: TextParams, browser: Inject[Browser]) -> None:
    await browser.input.insert_text(params.text)


@channel.method("browser.input.paste")
async def paste(params: TextParams, browser: Inject[Browser]) -> None:
    await browser.input.paste(params.text)
