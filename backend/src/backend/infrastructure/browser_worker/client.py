from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, cast

from httpx2 import AsyncClient, HTTPError
from pydantic import ValidationError

from backend.infrastructure.browser_worker.errors import (
    BrowserWorkerError,
    BrowserWorkerResponseError,
)
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from backend.presentation.middleware import current_request_id
from generated.browser_worker import ApiError, GeneratedBrowserWorkerClient


class BrowserWorkerClient:
    def __init__(self, http: AsyncClient, settings: BrowserWorkerSettings) -> None:
        self._http = http
        self._settings = settings

    async def request[T](
        self,
        base_url: str,
        operation: Callable[[GeneratedBrowserWorkerClient], Awaitable[T]],
        *,
        transfer: bool = False,
    ) -> T:
        client = GeneratedBrowserWorkerClient(
            cast(Any, self._http),
            base_url,
            headers=_request_headers(),
            timeout=self._timeout(transfer),
        )
        try:
            return await operation(client)
        except ApiError as error:
            code = getattr(error.parsed_body, "code", None)
            raise BrowserWorkerResponseError(error.status_code, code) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise BrowserWorkerError("Browser worker request failed") from error

    @asynccontextmanager
    async def stream(
        self,
        base_url: str,
        path: str,
    ) -> AsyncIterator[AsyncIterator[bytes]]:
        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            async with self._http.stream(
                "GET",
                url,
                headers=_request_headers(),
                timeout=self._settings.transfer_timeout_seconds,
            ) as response:
                response.raise_for_status()
                yield response.aiter_bytes(chunk_size=64 * 1024)
        except HTTPError as error:
            raise BrowserWorkerError("Browser worker stream failed") from error

    def _timeout(self, transfer: bool) -> float:
        if transfer:
            return self._settings.transfer_timeout_seconds
        return self._settings.request_timeout_seconds


def _request_headers() -> dict[str, str] | None:
    request_id = current_request_id()
    return {"X-Request-ID": request_id} if request_id is not None else None
