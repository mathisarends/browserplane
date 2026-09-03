import asyncio
import logging
from contextlib import suppress

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

logger = logging.getLogger(__name__)


async def proxy_cdp(client: WebSocket, upstream_url: str) -> None:
    await client.accept()
    try:
        async with connect(upstream_url, max_size=None) as upstream:
            await _relay(client, upstream)
        await _close_client(client, code=1000)
    except WebSocketDisconnect:
        pass
    except ConnectionClosedOK:
        await _close_client(client, code=1000)
    except (OSError, TimeoutError, ConnectionClosedError) as error:
        logger.warning(
            "Browser CDP connection became unavailable (%s)",
            type(error).__name__,
        )
        await _close_client(client, code=1011, reason="Browser CDP unavailable")
    except Exception as error:
        # Upstream URLs may contain credentials, so don't log exception messages.
        logger.error(
            "CDP websocket proxy stopped unexpectedly (%s)",
            type(error).__name__,
        )
        await _close_client(client, code=1011, reason="Browser CDP unavailable")


async def _relay(client: WebSocket, upstream: ClientConnection) -> None:
    tasks = {
        asyncio.create_task(_forward_client(client, upstream)),
        asyncio.create_task(_forward_upstream(upstream, client)),
    }
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _close_client(
    client: WebSocket,
    *,
    code: int,
    reason: str | None = None,
) -> None:
    if (
        client.client_state is WebSocketState.CONNECTED
        and client.application_state is WebSocketState.CONNECTED
    ):
        with suppress(RuntimeError):
            await client.close(code=code, reason=reason)


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
