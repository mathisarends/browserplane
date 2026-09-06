import asyncio
from collections.abc import Coroutine
from typing import Any

from fastapi import HTTPException, Request

CLIENT_CLOSED_REQUEST = 499
POLL_INTERVAL_SECONDS = 0.5


async def while_connected[T](http_request: Request, work: Coroutine[Any, Any, T]) -> T:
    """Run work only as long as the client is still there to receive it.

    A request that waits for a browser can outlive the browser tab that sent
    it. Starlette does not cancel the handler on its own, so the disconnect is
    polled next to the work and cancels it, letting the work undo what it
    started.
    """
    task = asyncio.create_task(work)
    watch = asyncio.create_task(_disconnected(http_request))
    try:
        done, _ = await asyncio.wait((task, watch), return_when=asyncio.FIRST_COMPLETED)
        if task in done:
            return task.result()
        raise HTTPException(CLIENT_CLOSED_REQUEST, "Client disconnected")
    finally:
        task.cancel()
        watch.cancel()
        await asyncio.gather(task, watch, return_exceptions=True)


async def _disconnected(http_request: Request) -> None:
    while not await http_request.is_disconnected():
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
