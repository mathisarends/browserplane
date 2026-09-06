import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from backend.features.browser_tunnel.application import (
    BrowserClipboard,
    BrowserInput,
    BrowserNavigation,
    KeyEventType,
    MouseEventType,
)

if TYPE_CHECKING:
    from backend.features.browser_tunnel.infrastructure.cdp_browser.page import CdpPage


class ActivePage:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.page: CdpPage | None = None

    @asynccontextmanager
    async def use(self) -> AsyncGenerator[CdpPage]:
        async with self.lock:
            if self.page is None:
                raise RuntimeError("No browser tab is active")
            yield self.page


class ActiveInput(BrowserInput):
    def __init__(self, active: ActivePage) -> None:
        self._active = active

    async def mouse(
        self,
        *,
        event_type: MouseEventType,
        x: float,
        y: float,
        button: str,
        buttons: int,
        modifiers: int,
        click_count: int,
    ) -> None:
        async with self._active.use() as page:
            return await page.input.mouse(
                event_type=event_type,
                x=x,
                y=y,
                button=button,
                buttons=buttons,
                modifiers=modifiers,
                click_count=click_count,
            )

    async def scroll(
        self, *, x: float, y: float, delta_x: float, delta_y: float
    ) -> None:
        async with self._active.use() as page:
            return await page.input.scroll(x=x, y=y, delta_x=delta_x, delta_y=delta_y)

    async def key(
        self,
        *,
        event_type: KeyEventType,
        key: str,
        code: str,
        text: str | None,
        unmodified_text: str | None,
        modifiers: int,
        auto_repeat: bool,
        windows_virtual_key_code: int,
        native_virtual_key_code: int,
        location: int,
        is_keypad: bool,
        is_system_key: bool,
    ) -> None:
        async with self._active.use() as page:
            return await page.input.key(
                event_type=event_type,
                key=key,
                code=code,
                text=text,
                unmodified_text=unmodified_text,
                modifiers=modifiers,
                auto_repeat=auto_repeat,
                windows_virtual_key_code=windows_virtual_key_code,
                native_virtual_key_code=native_virtual_key_code,
                location=location,
                is_keypad=is_keypad,
                is_system_key=is_system_key,
            )

    async def insert_text(self, text: str) -> None:
        async with self._active.use() as page:
            return await page.input.insert_text(text=text)

    async def paste(self, text: str) -> None:
        async with self._active.use() as page:
            return await page.input.paste(text=text)


class ActiveNavigation(BrowserNavigation):
    def __init__(self, active: ActivePage) -> None:
        self._active = active

    async def navigate(self, url: str) -> None:
        async with self._active.use() as page:
            return await page.navigation.navigate(url=url)

    async def back(self) -> None:
        async with self._active.use() as page:
            return await page.navigation.back()

    async def forward(self) -> None:
        async with self._active.use() as page:
            return await page.navigation.forward()

    async def reload(self, *, ignore_cache: bool = False) -> None:
        async with self._active.use() as page:
            return await page.navigation.reload(ignore_cache=ignore_cache)

    async def stop(self) -> None:
        async with self._active.use() as page:
            return await page.navigation.stop()


class ActiveClipboard(BrowserClipboard):
    def __init__(self, active: ActivePage) -> None:
        self._active = active

    async def copy(self) -> str:
        async with self._active.use() as page:
            return await page.clipboard.copy()

    async def read(self) -> str:
        async with self._active.use() as page:
            return await page.clipboard.read()

    async def write(self, text: str) -> None:
        async with self._active.use() as page:
            return await page.clipboard.write(text=text)
