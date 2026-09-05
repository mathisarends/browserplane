import asyncio
from types import SimpleNamespace

import pytest
from httpx2 import AsyncClient

from backend.infrastructure.browser_worker import (
    BrowserWorkerClient,
    BrowserWorkerResponseError,
)
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from generated.browser_worker import ApiError, GeneratedBrowserWorkerClient


def test_worker_response_errors_keep_their_machine_code() -> None:
    async def exercise() -> None:
        async def fail(client: GeneratedBrowserWorkerClient) -> None:
            raise ApiError(
                404,
                "not found",
                parsed_body=SimpleNamespace(code="recording_not_found"),
            )

        async with AsyncClient() as http:
            client = BrowserWorkerClient(
                http,
                BrowserWorkerSettings(_env_file=None),
            )
            with pytest.raises(BrowserWorkerResponseError) as raised:
                await client.request("http://worker", fail)

        assert raised.value.status_code == 404
        assert raised.value.code == "recording_not_found"

    asyncio.run(exercise())
