import logging
from collections.abc import Awaitable, Callable

from pydantic import ValidationError

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
from backend.features.sessions.application.ports import BrowserRuntime
from backend.infrastructure.browser_worker import (
    BrowserWorkerClient,
    BrowserWorkerError,
    BrowserWorkerResponseError,
)
from generated.browser_worker import (
    AuthenticationStateSchema,
    BrowserStateSchema,
    GeneratedBrowserWorkerClient,
)

logger = logging.getLogger(__name__)


class BrowserWorkerRuntime(BrowserRuntime):
    def __init__(self, client: BrowserWorkerClient) -> None:
        self._client = client

    async def capture_authentication(
        self, browser: Browser
    ) -> AuthenticationStateDocument:
        state = await self._request(
            browser,
            "read authentication from",
            lambda client: client.capture_authentication_state(browser.id),
        )
        return state.model_dump(mode="json", by_alias=True)

    async def mount_authentication(
        self, browser: Browser, state: AuthenticationStateDocument
    ) -> None:
        try:
            body = AuthenticationStateSchema.model_validate(state)
        except ValidationError as error:
            raise _as_transfer_failure("validate authentication for", error) from error
        await self._request(
            browser,
            "write authentication to",
            lambda client: client.mount_authentication_state(browser.id, body),
        )

    async def capture_browser(self, browser: Browser) -> BrowserStateDocument:
        state = await self._request(
            browser,
            "read browser state from",
            lambda client: client.capture_browser_state(browser.id),
        )
        return state.model_dump(mode="json", by_alias=True)

    async def mount_browser(
        self, browser: Browser, state: BrowserStateDocument
    ) -> None:
        try:
            body = BrowserStateSchema.model_validate(state)
        except ValidationError as error:
            raise _as_transfer_failure("validate browser state for", error) from error
        await self._request(
            browser,
            "write browser state to",
            lambda client: client.mount_browser_state(browser.id, body),
        )

    async def list_downloads(self, browser: Browser) -> tuple[Download, ...]:
        downloads = await self._request(
            browser,
            "read downloads from",
            lambda client: client.list_downloads(browser.id),
        )
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
        await self._request(
            browser,
            "clear downloads on",
            lambda client: client.clear_downloads(browser.id),
        )

    async def download_file(self, browser: Browser, download_id: str) -> bytes:
        try:
            return await self._client.request(
                browser.slot.browser_worker_url,
                lambda client: client.download_file(browser.id, download_id),
            )
        except BrowserWorkerResponseError as error:
            if error.code == "download_not_found":
                raise DownloadNotFoundException() from error
            raise _as_transfer_failure("download file from", error) from error
        except BrowserWorkerError as error:
            raise _as_transfer_failure("download file from", error) from error

    async def _request[T](
        self,
        browser: Browser,
        action: str,
        operation: Callable[[GeneratedBrowserWorkerClient], Awaitable[T]],
    ) -> T:
        try:
            return await self._client.request(
                browser.slot.browser_worker_url,
                operation,
            )
        except BrowserWorkerError as error:
            raise _as_transfer_failure(action, error) from error


def _as_transfer_failure(
    action: str,
    error: Exception,
) -> BrowserStateTransferException:
    logger.warning("Could not %s browser: %s", action, type(error).__name__)
    return BrowserStateTransferException(f"Could not {action} browser")
