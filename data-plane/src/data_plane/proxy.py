import asyncio
from contextlib import suppress

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed


async def proxy_cdp(client: WebSocket, upstream_url: str) -> None:
    await client.accept()
    try:
        async with connect(upstream_url, max_size=None) as upstream:
            tasks = {
                asyncio.create_task(_forward_client(client, upstream)),
                asyncio.create_task(_forward_upstream(upstream, client)),
            }
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            for task in done | pending:
                with suppress(
                    asyncio.CancelledError, ConnectionClosed, WebSocketDisconnect
                ):
                    await task
    except OSError:
        await client.close(code=1011, reason="Browser CDP unavailable")


async def _forward_client(client: WebSocket, upstream: ClientConnection) -> None:
    while True:
        message = await client.receive()
        if message["type"] == "websocket.disconnect":
            return
        if (text := message.get("text")) is not None:
            await upstream.send(text)
        elif (data := message.get("bytes")) is not None:
            await upstream.send(data)


async def _forward_upstream(upstream: ClientConnection, client: WebSocket) -> None:
    async for message in upstream:
        if isinstance(message, str):
            await client.send_text(message)
        else:
            await client.send_bytes(message)
