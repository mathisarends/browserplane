"""Start the real browser adapter once and verify its CDP connection."""

import asyncio
from contextlib import aclosing

from browsertunnel.application import NavigationChanged
from browsertunnel.infrastructure.cdp_browser import CdpBrowser
from browsertunnel.settings import BrowserSettings


async def next_navigation(events) -> NavigationChanged:
    while True:
        event = await anext(events)
        if isinstance(event, NavigationChanged):
            return event


async def main() -> None:
    browser = CdpBrowser(BrowserSettings(_env_file=None))
    await browser.start()
    try:
        tabs = await browser.tabs.list()
        print(f"CDP connected with {len(tabs)} tab(s)")
        async with aclosing(browser.events()) as events:
            navigation_task = asyncio.create_task(next_navigation(events))
            await asyncio.sleep(0)
            await browser.navigation.navigate(
                "data:text/html,<title>BrowserTunnel</title>"
            )
            navigation = await asyncio.wait_for(navigation_task, timeout=5)
            print(f"Navigation state received ({navigation.url})")
    finally:
        await browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
