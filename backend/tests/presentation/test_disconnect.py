import asyncio

import pytest

from backend.presentation.disconnect import while_connected


class SlowDisconnectRequest:
    """A transport whose receive side needs time to observe cancellation."""

    async def is_disconnected(self) -> bool:
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            await asyncio.sleep(0.1)
            raise
        return False


@pytest.mark.asyncio
async def test_completed_work_does_not_wait_for_disconnect_cleanup() -> None:
    result = await asyncio.wait_for(
        while_connected(SlowDisconnectRequest(), asyncio.sleep(0, result="done")),
        timeout=0.05,
    )

    assert result == "done"
