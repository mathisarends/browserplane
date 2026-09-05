import logging

from httpx2 import AsyncClient

from backend.features.browsers.application.models import Browser
from backend.features.sessions.application.exceptions import (
    BrowserStateTransferException,
)
from backend.features.sessions.application.models import BrowserStateDocument
from backend.features.sessions.application.ports import BrowserStateGateway
from generated.data_plane import BrowserStateSchema, GeneratedDataPlaneClient

logger = logging.getLogger(__name__)


class DataPlaneBrowserStateGateway(BrowserStateGateway):
    """Move a browser's state between its worker and our database.

    The payload is passed through as the document the data plane defined; the
    backend only decides where it is stored and for how long.
    """

    async def capture(self, browser: Browser) -> BrowserStateDocument:
        try:
            async with AsyncClient() as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                state = await client.capture_browser_state(browser.id)
        except Exception as error:
            raise _as_transfer_failure("read", error) from error
        return state.model_dump(mode="json", by_alias=True)

    async def mount(self, browser: Browser, state: BrowserStateDocument) -> None:
        try:
            body = BrowserStateSchema.model_validate(state)
            async with AsyncClient() as http:
                client = GeneratedDataPlaneClient(http, browser.slot.data_plane_url)
                await client.mount_browser_state(browser.id, body)
        except Exception as error:
            raise _as_transfer_failure("write", error) from error


def _as_transfer_failure(
    action: str,
    error: Exception,
) -> BrowserStateTransferException:
    """Report that the transfer failed without quoting cookies into the logs."""
    logger.warning("Could not %s the browser state: %s", action, type(error).__name__)
    return BrowserStateTransferException(f"Could not {action} the browser state")
