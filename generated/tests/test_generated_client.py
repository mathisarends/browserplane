import pytest
from httpx2 import ASGITransport, AsyncClient

from data_plane.app import create_app
from generated.data_plane import GeneratedDataPlaneClient, HealthStatus


@pytest.mark.asyncio
async def test_generated_client_reaches_the_data_plane() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport) as http:
        client = GeneratedDataPlaneClient(http, "http://data-plane")
        health = await client.health()
    assert health.status is HealthStatus.OK
