"""HTTP transport shared by the generated clients."""

from typing import Any

from httpx2 import AsyncClient, Response

DEFAULT_TIMEOUT = 10.0


class HttpTransport:
    """Sends the requests of a generated client against one base URL."""

    def __init__(
        self,
        base_url: str,
        *,
        client: AsyncClient | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._owned = client is None
        self._client = client or AsyncClient(timeout=timeout)
        self._base_url = base_url.rstrip("/")

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
    ) -> Response:
        """Perform the request and raise on any non-success status."""
        response = await self._client.request(
            method,
            f"{self._base_url}{path}",
            params=_present(params),
            json=json,
        )
        response.raise_for_status()
        return response

    async def aclose(self) -> None:
        if self._owned:
            await self._client.aclose()

    async def __aenter__(self) -> HttpTransport:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


def _present(params: dict[str, Any] | None) -> dict[str, Any] | None:
    """Drop unset query parameters so they are not sent as empty values."""
    if params is None:
        return None
    return {name: value for name, value in params.items() if value is not None}
