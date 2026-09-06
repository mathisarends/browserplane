import logging
from typing import Any, cast

from httpx2 import AsyncClient, HTTPError
from pydantic import ValidationError

from backend.features.browsers.domain.models import Browser
from backend.features.sessions.application.exceptions import (
    BrowserStateTransferException,
    DownloadNotFoundException,
)
from backend.features.sessions.application.ports import BrowserRuntime
from backend.features.sessions.domain.models import (
    AuthenticationStateDocument,
    BrowserStateDocument,
    Download,
)
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from generated.browser_worker import (
    ApiError,
    AuthenticationState,
    BrowserState,
    GeneratedBrowserWorkerClient,
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
            state = await self._client(browser).capture_authentication_state(browser.id)
        except (ApiError, HTTPError, ValidationError, ValueError) as error:
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
            await self._client(browser).mount_authentication_state(browser.id, body)
        except (ApiError, HTTPError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("write authentication to", error) from error

    async def capture_browser(self, browser: Browser) -> BrowserStateDocument:
        try:
            state = await self._client(browser).capture_browser_state(browser.id)
        except (ApiError, HTTPError, ValidationError, ValueError) as error:
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
            await self._client(browser).mount_browser_state(browser.id, body)
        except (ApiError, HTTPError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("write browser state to", error) from error

    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]:
        try:
            downloads = await self._client(browser).list_downloads(browser.id)
        except (ApiError, HTTPError, ValidationError, ValueError) as error:
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
            await self._client(browser).clear_downloads(browser.id)
        except (ApiError, HTTPError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("clear downloads on", error) from error

    async def download_file(self, browser: Browser, download_id: str) -> bytes:
        try:
            return await self._client(browser).download_file(browser.id, download_id)
        except ApiError as error:
            if getattr(error.parsed_body, "code", None) == "download_not_found":
                raise DownloadNotFoundException() from error
            raise _as_transfer_failure("download file from", error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _as_transfer_failure("download file from", error) from error

    def _client(self, browser: Browser) -> GeneratedBrowserWorkerClient:
        return GeneratedBrowserWorkerClient(
            cast(Any, self._http),
            browser.slot.browser_worker_url,
            timeout=self._settings.request_timeout_seconds,
        )


def _as_transfer_failure(
    action: str,
    error: Exception,
) -> BrowserStateTransferException:
    logger.warning("Could not %s browser: %s", action, type(error).__name__)
    return BrowserStateTransferException(f"Could not {action} browser")
