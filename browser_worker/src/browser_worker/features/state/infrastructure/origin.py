import asyncio
import base64
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from cdpify import CDPSession, Client
from cdpify.domains.fetch.events import FetchEvent, RequestPausedEvent
from cdpify.domains.fetch.types import HeaderEntry, RequestPattern
from cdpify.domains.page.events import LoadEventFiredEvent, PageEvent

from browser_worker.features.state.application.exceptions import (
    BrowserStateFailedException,
)

_BLANK_URL = "about:blank"
_EMPTY_DOCUMENT = base64.b64encode(b"<!doctype html><title>storage</title>").decode()


@asynccontextmanager
async def loaded_origin(client: Client, origin: str) -> AsyncGenerator[CDPSession]:
    """Open an inert document with access to an origin's persistent storage."""
    created = await client.target.create_target(url=_BLANK_URL, background=True)
    try:
        attached = await client.target.attach_to_target(
            target_id=created.target_id,
            flatten=True,
        )
        session = client.session(attached.session_id)
        try:
            await session.page.enable()
            await session.fetch.enable(
                patterns=[RequestPattern(resource_type="Document")]
            )
            document = asyncio.create_task(
                _fulfill_empty_document(session, timeout=10),
                name=f"browser-state:document:{created.target_id}",
            )
            loaded = asyncio.create_task(
                _wait_for_load(session, timeout=10),
                name=f"browser-state:origin:{created.target_id}",
            )
            try:
                await asyncio.sleep(0)
                navigation = await session.page.navigate(url=origin)
                if navigation.error_text:
                    raise BrowserStateFailedException(navigation.error_text)
                await document
                await loaded
            finally:
                document.cancel()
                loaded.cancel()
                with suppress(BaseException):
                    await document
                with suppress(BaseException):
                    await loaded
            yield session
        finally:
            with suppress(Exception):
                await client.target.detach_from_target(session_id=session.session_id)
    finally:
        with suppress(Exception):
            await client.target.close_target(target_id=created.target_id)


async def _fulfill_empty_document(session: CDPSession, timeout: float) -> None:
    async for event in session.listen(
        FetchEvent.REQUEST_PAUSED,
        RequestPausedEvent,
        timeout=timeout,
    ):
        await session.fetch.fulfill_request(
            request_id=event.request_id,
            response_code=200,
            response_headers=[
                HeaderEntry(name="Content-Type", value="text/html; charset=utf-8")
            ],
            body=_EMPTY_DOCUMENT,
        )
        return


async def _wait_for_load(session: CDPSession, timeout: float) -> None:
    async for _ in session.listen(
        PageEvent.LOAD_EVENT_FIRED,
        LoadEventFiredEvent,
        timeout=timeout,
    ):
        return
