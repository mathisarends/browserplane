# Generated from control_plane-openapi.json. Do not edit manually.

from uuid import UUID

from httpx2 import AsyncClient
from pydantic import TypeAdapter

from generated.transport import HttpTransport

from .models import BrowserResponse, CreateLeaseRequest, LeaseResponse


class ControlPlaneClient:
    """Typed async client for Browser Control Plane 0.1.0."""

    def __init__(
        self,
        base_url: str,
        *,
        client: AsyncClient | None = None,
    ) -> None:
        self._transport = HttpTransport(base_url, client=client)

    async def __aenter__(self) -> ControlPlaneClient:
        await self._transport.__aenter__()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._transport.__aexit__(*exc_info)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def health(self) -> dict[str, str]:
        """Health."""
        response = await self._transport.request(
            "GET",
            "/api/v1/health",
        )
        return TypeAdapter(dict[str, str]).validate_python(response.json())

    async def readiness(self) -> dict[str, str]:
        """Readiness."""
        response = await self._transport.request(
            "GET",
            "/api/v1/readiness",
        )
        return TypeAdapter(dict[str, str]).validate_python(response.json())

    async def list_browsers(self) -> list[BrowserResponse]:
        """List Browsers."""
        response = await self._transport.request(
            "GET",
            "/api/v1/browsers",
        )
        return TypeAdapter(list[BrowserResponse]).validate_python(response.json())

    async def create_browser(self) -> BrowserResponse:
        """Create Browser."""
        response = await self._transport.request(
            "POST",
            "/api/v1/browsers",
        )
        return BrowserResponse.model_validate(response.json())

    async def get_browser(self, browser_id: UUID) -> BrowserResponse:
        """Get Browser."""
        response = await self._transport.request(
            "GET",
            f"/api/v1/browsers/{browser_id}",
        )
        return BrowserResponse.model_validate(response.json())

    async def destroy_browser(self, browser_id: UUID) -> None:
        """Destroy Browser."""
        await self._transport.request(
            "DELETE",
            f"/api/v1/browsers/{browser_id}",
        )

    async def reset_browser(self, browser_id: UUID) -> BrowserResponse:
        """Reset Browser."""
        response = await self._transport.request(
            "POST",
            f"/api/v1/browsers/{browser_id}/reset",
        )
        return BrowserResponse.model_validate(response.json())

    async def create_lease(self, body: CreateLeaseRequest) -> LeaseResponse:
        """Create Lease."""
        response = await self._transport.request(
            "POST",
            "/api/v1/leases",
            json=body.model_dump(mode="json"),
        )
        return LeaseResponse.model_validate(response.json())

    async def get_lease(self, lease_id: UUID) -> LeaseResponse:
        """Get Lease."""
        response = await self._transport.request(
            "GET",
            f"/api/v1/leases/{lease_id}",
        )
        return LeaseResponse.model_validate(response.json())

    async def release_lease(self, lease_id: UUID) -> None:
        """Release Lease."""
        await self._transport.request(
            "DELETE",
            f"/api/v1/leases/{lease_id}",
        )
