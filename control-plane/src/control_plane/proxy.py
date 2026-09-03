import asyncio
from contextlib import suppress

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed


async def proxy_websocket(client: WebSocket, tunnel_url: str) -> None:
    await client.accept()
    try:
        async with connect(tunnel_url, max_size=None) as tunnel:
            tasks = {
                asyncio.create_task(_forward_to_tunnel(client, tunnel)),
                asyncio.create_task(_forward_to_client(tunnel, client)),
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
        await client.close(code=1011, reason="Browser tunnel unavailable")


async def _forward_to_tunnel(
    client: WebSocket, tunnel: ClientConnection
) -> None:
    while True:
        message = await client.receive()
        if message["type"] == "websocket.disconnect":
            return
        if (text := message.get("text")) is not None:
            await tunnel.send(text)
        elif (data := message.get("bytes")) is not None:
            await tunnel.send(data)


async def _forward_to_client(
    tunnel: ClientConnection, client: WebSocket
) -> None:
    async for message in tunnel:
        if isinstance(message, str):
            await client.send_text(message)
        else:
            await client.send_bytes(message)
