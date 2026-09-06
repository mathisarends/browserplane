from enum import StrEnum
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID

from backend.features.browsers.domain.models import BrowserSlot

_BROWSER_PATH = "/api/v1/browser"


class ScreencastMode(StrEnum):
    """How the worker packages captured frames for the client."""

    JPEG = "jpeg"
    DIRTY_RECTANGLES = "dirty-rectangles"
    FMP4 = "fmp4"


class BrowserWorkerRoutes:
    def cdp_url(self, slot: BrowserSlot) -> str:
        return self._stream_url(slot, "cdp")

    def screencast_url(self, slot: BrowserSlot, mode: ScreencastMode) -> str:
        return self._stream_url(slot, "screencast", query={"mode": mode.value})

    def recording_file_url(self, slot: BrowserSlot, recording_id: UUID) -> str:
        parsed = urlsplit(slot.browser_worker_url)
        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                f"{self._base_path(parsed.path)}/{slot.id}/recordings/"
                f"{recording_id}/file",
                "",
                "",
            )
        )

    def _stream_url(
        self, slot: BrowserSlot, stream: str, query: dict[str, str] | None = None
    ) -> str:
        parsed = urlsplit(slot.browser_worker_url)
        return urlunsplit(
            (
                "wss" if parsed.scheme == "https" else "ws",
                parsed.netloc,
                f"{self._base_path(parsed.path)}/{slot.id}/{stream}",
                urlencode(query) if query else "",
                "",
            )
        )

    def _base_path(self, worker_path: str) -> str:
        return f"{worker_path.rstrip('/')}{_BROWSER_PATH}"
