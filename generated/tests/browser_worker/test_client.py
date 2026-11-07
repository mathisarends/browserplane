import pytest
from httpx2 import ASGITransport, AsyncClient

from browser_worker.app import create_app
from generated.browser_worker import BrowserWorkerClient, HealthStatus


@pytest.mark.asyncio
async def test_generated_client_reaches_the_browser_worker() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport) as http:
        async with BrowserWorkerClient(http, "http://browser-worker") as client:
            health = await client.health()
        assert not http.is_closed
    assert health.status is HealthStatus.OK
