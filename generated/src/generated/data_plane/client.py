# Generated from data_plane-openapi.json. Do not edit manually.

from httpx2 import AsyncClient

from generated.transport import HttpTransport

from .models import BrowserResponse, CreateBrowserRequest, HealthResponse


class DataPlaneClient:
    """Typed async client for Browser Data Plane 0.1.0."""

    def __init__(
        self,
        base_url: str,
        *,
        client: AsyncClient | None = None,
    ) -> None:
        self._transport = HttpTransport(base_url, client=client)

    async def __aenter__(self) -> DataPlaneClient:
        await self._transport.__aenter__()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._transport.__aexit__(*exc_info)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def health(self) -> HealthResponse:
        """Health."""
        response = await self._transport.request(
            "GET",
            "/api/v1/health",
        )
        return HealthResponse.model_validate(response.json())

    async def readiness(self) -> HealthResponse:
        """Readiness."""
        response = await self._transport.request(
            "GET",
            "/api/v1/readiness",
        )
        return HealthResponse.model_validate(response.json())

    async def inspect_browser(self) -> BrowserResponse:
        """Inspect Browser."""
        response = await self._transport.request(
            "GET",
            "/api/v1/browser",
        )
        return BrowserResponse.model_validate(response.json())

    async def create_browser(self, body: CreateBrowserRequest) -> BrowserResponse:
        """Create Browser."""
        response = await self._transport.request(
            "POST",
            "/api/v1/browser",
            json=body.model_dump(mode="json"),
        )
        return BrowserResponse.model_validate(response.json())

    async def destroy_browser(self) -> None:
        """Destroy Browser."""
        await self._transport.request(
            "DELETE",
            "/api/v1/browser",
        )
