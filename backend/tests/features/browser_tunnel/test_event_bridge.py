import asyncio
from typing import cast
from unittest.mock import AsyncMock

import pytest
from cdpify import Client
from cdpify.domains.target.events import TargetCrashedEvent as CdpTargetCrashedEvent
from cdpify.domains.target.events import TargetEvent

from backend.features.browser_tunnel.application import BrowserEvent, TargetCrashed
from backend.features.browser_tunnel.infrastructure.events import BrowserEventStream
from backend.features.browser_tunnel.infrastructure.target_event_bridge import (
    TargetEventBridge,
)


class FakeListenerSource:
    def __init__(self) -> None:
        self.event_names: set[str] = set()
        self.queues: dict[str, asyncio.Queue[object]] = {}

    async def listen[T](
        self,
        event_name: str,
        event_type: type[T],
        timeout: float | None = None,
    ):
        self.event_names.add(event_name)
        queue = self.queues.setdefault(event_name, asyncio.Queue())
        while True:
            yield cast(T, await queue.get())

    async def emit(self, event_name: str, event: object) -> None:
        await self.queues[event_name].put(event)


@pytest.mark.asyncio
async def test_event_stream_delivers_events_to_subscribers() -> None:
    stream = BrowserEventStream()
    event = TargetCrashed("tab-1", "crashed", 7)
    with stream.subscribe() as queue:
        stream.publish(event)
        assert await queue.get() == event


@pytest.mark.asyncio
async def test_target_bridge_owns_cdp_listener_registration() -> None:
    domain_events: list[BrowserEvent] = []
    received = asyncio.Event()

    def collect(event: BrowserEvent) -> None:
        domain_events.append(event)
        received.set()

    source = FakeListenerSource()
    bridge = TargetEventBridge(collect, AsyncMock(), AsyncMock(), lambda: None)
    await bridge.start(cast(Client, source))
    try:
        assert source.event_names == {
            event.value
            for event in (
                TargetEvent.TARGET_CREATED,
                TargetEvent.TARGET_DESTROYED,
                TargetEvent.TARGET_INFO_CHANGED,
                TargetEvent.TARGET_CRASHED,
                TargetEvent.DETACHED_FROM_TARGET,
            )
        }

        cdp_event = CdpTargetCrashedEvent(
            target_id="tab-1", status="crashed", error_code=7
        )
        await source.emit(TargetEvent.TARGET_CRASHED, cdp_event)
        await asyncio.wait_for(received.wait(), timeout=1)

        assert domain_events == [TargetCrashed("tab-1", "crashed", 7)]
    finally:
        await bridge.stop()
