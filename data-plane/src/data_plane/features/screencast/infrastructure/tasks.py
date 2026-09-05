import asyncio


async def cancel_and_wait(*tasks: asyncio.Task[object]) -> None:
    """Cancel running tasks and consume every completion result."""
    for task in tasks:
        if not task.done():
            task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
