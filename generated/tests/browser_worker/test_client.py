import pytest
from httpx2 import ASGITransport, AsyncClient

from browser_worker.app import create_app
from generated.browser_worker import GeneratedBrowserWorkerClient, HealthStatus


@pytest.mark.asyncio
async def test_generated_client_reaches_the_browser_worker() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport) as http:
        client = GeneratedBrowserWorkerClient(http, "http://browser-worker")
        health = await client.health()
    assert health.status is HealthStatus.OK
