import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from cdpify import CDPSession

from backend.features.browser_tunnel.application import (
    BrowserEvent,
    CursorChanged,
    CursorStyle,
)
from backend.features.browser_tunnel.infrastructure.cursor_event_bridge import (
    CursorEventBridge,
)


class FakePage:
    def __init__(self) -> None:
        self.injected_with: dict | None = None

    async def add_script_to_evaluate_on_new_document(self, **kwargs):
        self.injected_with = kwargs
        return SimpleNamespace(identifier="cursor-script")

    async def remove_script_to_evaluate_on_new_document(self, **kwargs) -> None:
        pass


class FakeRuntime:
    def __init__(self) -> None:
        self.enabled = False
        self.binding_with: dict | None = None

    async def enable(self) -> None:
        self.enabled = True

    async def add_binding(self, **kwargs) -> None:
        self.binding_with = kwargs

    async def remove_binding(self, **kwargs) -> None:
        pass


class FakeSession:
    def __init__(self, *payloads: str, name: str = "__browserTunnelCursor") -> None:
        self.page = FakePage()
        self.runtime = FakeRuntime()
        self._payloads = payloads
        self._name = name

    async def listen(self, *_args):
        for payload in self._payloads:
            yield SimpleNamespace(
                name=self._name, payload=payload, execution_context_id=1
            )
        await asyncio.Future()


async def drain(received: list[BrowserEvent], expected: int) -> None:
    async with asyncio.timeout(1):
        while len(received) < expected:
            await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_cursor_bridge_installs_observer_in_an_isolated_world() -> None:
    bridge = CursorEventBridge(lambda event: None)
    session = FakeSession()

    await bridge.start(cast(CDPSession, session), "tab-1")
    await asyncio.sleep(0)
    await bridge.stop()

    assert session.runtime.enabled
    assert session.runtime.binding_with == {
        "name": "__browserTunnelCursor",
        "execution_context_name": "browsertunnel:cursor",
    }
    assert session.page.injected_with is not None
    assert session.page.injected_with["world_name"] == "browsertunnel:cursor"
    assert session.page.injected_with["run_immediately"] is True


@pytest.mark.asyncio
async def test_cursor_bridge_dispatches_only_actual_changes() -> None:
    received: list[BrowserEvent] = []
    bridge = CursorEventBridge(received.append)
    session = FakeSession("pointer", "pointer", "text")

    await bridge.start(cast(CDPSession, session), "tab-1")
    await drain(received, 2)
    await bridge.stop()

    assert received == [
        CursorChanged("tab-1", CursorStyle.POINTER),
        CursorChanged("tab-1", CursorStyle.TEXT),
    ]


@pytest.mark.asyncio
async def test_cursor_bridge_falls_back_to_default_for_unknown_cursors() -> None:
    received: list[BrowserEvent] = []
    bridge = CursorEventBridge(received.append)
    session = FakeSession("pointer", 'url("evil.png"), pointer')

    await bridge.start(cast(CDPSession, session), "tab-1")
    await drain(received, 2)
    await bridge.stop()

    assert received == [
        CursorChanged("tab-1", CursorStyle.POINTER),
        CursorChanged("tab-1", CursorStyle.DEFAULT),
    ]
