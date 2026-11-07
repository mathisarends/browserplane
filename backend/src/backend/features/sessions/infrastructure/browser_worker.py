import logging

from httpx2 import AsyncClient
from pydantic import ValidationError

from backend.features.browsers.domain import Browser
from backend.features.sessions.application import (
    BrowserStateTransferException,
    DownloadNotFoundException,
)
from backend.features.sessions.domain import (
    AuthenticationStateDocument,
    BrowserRuntime,
    BrowserStateDocument,
    Download,
)
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from generated.browser_worker import (
    ApiError,
    AuthenticationState,
    BrowserState,
    BrowserWorkerClient,
    ClientError,
)

logger = logging.getLogger(__name__)


class BrowserWorkerRuntime(BrowserRuntime):
    def __init__(
        self,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
    ) -> None:
        self._http = http
        self._settings = settings

    async def capture_authentication(
        self, browser: Browser
    ) -> AuthenticationStateDocument:
        try:
            client = self._client(browser)
            state = await client.capture_authentication_state()
        except (ClientError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("read authentication from", error) from error
        return state.model_dump(mode="json", by_alias=True)

    async def mount_authentication(
        self, browser: Browser, state: AuthenticationStateDocument
    ) -> None:
        try:
            body = AuthenticationState.model_validate(state)
        except ValidationError as error:
            raise _as_transfer_failure("validate authentication for", error) from error
        try:
            client = self._client(browser)
            await client.mount_authentication_state(body)
        except (ClientError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("write authentication to", error) from error

    async def capture_browser(self, browser: Browser) -> BrowserStateDocument:
        try:
            client = self._client(browser)
            state = await client.capture_browser_state()
        except (ClientError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("read browser state from", error) from error
        return state.model_dump(mode="json", by_alias=True)

    async def mount_browser(
        self, browser: Browser, state: BrowserStateDocument
    ) -> None:
        try:
            body = BrowserState.model_validate(state)
        except ValidationError as error:
            raise _as_transfer_failure("validate browser state for", error) from error
        try:
            client = self._client(browser)
            await client.mount_browser_state(body)
        except (ClientError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("write browser state to", error) from error

    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]:
        try:
            client = self._client(browser)
            downloads = await client.list_downloads()
        except (ClientError, ValidationError, ValueError) as error:
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
            client = self._client(browser)
            await client.clear_downloads()
        except (ClientError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("clear downloads on", error) from error

    async def download_file(self, browser: Browser, download_id: str) -> bytes:
        try:
            client = self._client(browser)
            return await client.download_file(download_id)
        except ApiError as error:
            if error.code == "download_not_found":
                raise DownloadNotFoundException() from error
            raise _as_transfer_failure("download file from", error) from error
        except (ClientError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("download file from", error) from error

    def _client(self, browser: Browser) -> BrowserWorkerClient:
        return BrowserWorkerClient(
            self._http,
            browser.slot.browser_worker_url,
            timeout=self._settings.request_timeout_seconds,
        )


def _as_transfer_failure(
    action: str,
    error: Exception,
) -> BrowserStateTransferException:
    logger.warning("Could not %s browser: %s", action, type(error).__name__)
    return BrowserStateTransferException(f"Could not {action} browser")
