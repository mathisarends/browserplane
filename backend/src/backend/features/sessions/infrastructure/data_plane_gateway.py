import logging

from httpx2 import AsyncClient

from backend.features.browsers.application.models import Browser
from backend.features.sessions.application.exceptions import (
    BrowserStateTransferException,
    DownloadNotFoundException,
)
from backend.features.sessions.application.models import (
    AuthenticationStateDocument,
    BrowserStateDocument,
    Download,
)
from backend.features.sessions.application.ports import BrowserStateGateway
from backend.request_logging import current_request_id
from generated.data_plane import (
    ApiError,
    AuthenticationStateSchema,
    BrowserStateSchema,
    GeneratedDataPlaneClient,
)

logger = logging.getLogger(__name__)


def _request_headers() -> dict[str, str] | None:
    request_id = current_request_id()
    return {"X-Request-ID": request_id} if request_id is not None else None


class DataPlaneBrowserStateGateway(BrowserStateGateway):
    """Move a browser's state between its worker and our database.

    The payload is passed through as the document the data plane defined; the
    backend only decides where it is stored and for how long.
    """

    async def capture_authentication(
        self, browser: Browser
    ) -> AuthenticationStateDocument:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                state = await client.capture_authentication_state(browser.id)
        except Exception as error:
            raise _as_transfer_failure("read authentication from", error) from error
        return state.model_dump(mode="json", by_alias=True)

    async def mount_authentication(
        self, browser: Browser, state: AuthenticationStateDocument
    ) -> None:
        try:
            body = AuthenticationStateSchema.model_validate(state)
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                await client.mount_authentication_state(browser.id, body)
        except Exception as error:
            raise _as_transfer_failure("write authentication to", error) from error

    async def capture_browser(self, browser: Browser) -> BrowserStateDocument:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                state = await client.capture_browser_state(browser.id)
        except Exception as error:
            raise _as_transfer_failure("read browser state from", error) from error
        return state.model_dump(mode="json", by_alias=True)

    async def mount_browser(
        self, browser: Browser, state: BrowserStateDocument
    ) -> None:
        try:
            body = BrowserStateSchema.model_validate(state)
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                await client.mount_browser_state(browser.id, body)
        except Exception as error:
            raise _as_transfer_failure("write browser state to", error) from error

    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                downloads = await client.list_downloads(browser.id)
        except Exception as error:
            raise _as_transfer_failure("read downloads from", error) from error
        return tuple(
            Download(
                id=item.id,
                filename=item.filename,
                url=item.url,
                size=item.size,
            )
            for item in downloads
        )

    async def clear_downloads(self, browser: Browser) -> None:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                await client.clear_downloads(browser.id)
        except Exception as error:
            raise _as_transfer_failure("clear downloads on", error) from error

    async def download_file(self, browser: Browser, download_id: str) -> bytes:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                return await client.download_file(browser.id, download_id)
        except ApiError as error:
            if getattr(error.parsed_body, "code", None) == "download_not_found":
                raise DownloadNotFoundException() from error
            raise _as_transfer_failure("download file from", error) from error
        except Exception as error:
            raise _as_transfer_failure("download file from", error) from error


def _as_transfer_failure(
    action: str,
    error: Exception,
) -> BrowserStateTransferException:
    """Report that the transfer failed without quoting cookies into the logs."""
    logger.warning("Could not %s browser: %s", action, type(error).__name__)
    return BrowserStateTransferException(f"Could not {action} browser")
