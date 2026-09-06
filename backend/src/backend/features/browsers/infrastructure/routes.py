from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from backend.features.browsers.domain.models import BrowserSlot

_BROWSER_PATH = "/api/v1/browser"


class BrowserWorkerRoutes:
    def cdp_url(self, slot: BrowserSlot) -> str:
        return self._stream_url(slot, "cdp")

    def screencast_url(self, slot: BrowserSlot) -> str:
        return self._stream_url(slot, "screencast")

    def fmp4_screencast_url(self, slot: BrowserSlot) -> str:
        return f"{self.screencast_url(slot)}/fmp4"

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

    def _stream_url(self, slot: BrowserSlot, stream: str) -> str:
        parsed = urlsplit(slot.browser_worker_url)
        return urlunsplit(
            (
                "wss" if parsed.scheme == "https" else "ws",
                parsed.netloc,
                f"{self._base_path(parsed.path)}/{slot.id}/{stream}",
                "",
                "",
            )
        )

    def _base_path(self, worker_path: str) -> str:
        return f"{worker_path.rstrip('/')}{_BROWSER_PATH}"
