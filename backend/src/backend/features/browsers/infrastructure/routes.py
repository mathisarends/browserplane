"""
How a browser on its worker is addressed.

The route table belongs to the browser worker's HTTP API, not to the pool's
domain model: renaming a worker route must not reach into a domain dataclass.
The HTTP routes come from the generated client; only the streams and the
raw file transfers are built here, because neither has a generated call.
"""

from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from backend.features.browsers.domain.models import BrowserSlot

BROWSER_PATH = "/api/v1/browser"


def cdp_url(slot: BrowserSlot) -> str:
    return _stream_url(slot, "cdp")


def screencast_url(slot: BrowserSlot) -> str:
    return _stream_url(slot, "screencast")


def fmp4_screencast_url(slot: BrowserSlot) -> str:
    return f"{screencast_url(slot)}/fmp4"


def recording_file_url(slot: BrowserSlot, recording_id: UUID) -> str:
    parsed = urlsplit(slot.browser_worker_url)
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            f"{_base_path(parsed.path)}/{slot.id}/recordings/{recording_id}/file",
            "",
            "",
        )
    )


def _stream_url(slot: BrowserSlot, stream: str) -> str:
    parsed = urlsplit(slot.browser_worker_url)
    return urlunsplit(
        (
            "wss" if parsed.scheme == "https" else "ws",
            parsed.netloc,
            f"{_base_path(parsed.path)}/{slot.id}/{stream}",
            "",
            "",
        )
    )


def _base_path(worker_path: str) -> str:
    return f"{worker_path.rstrip('/')}{BROWSER_PATH}"
