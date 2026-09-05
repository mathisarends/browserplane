import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from cdpify import Client
from cdpify.domains.browser.events import (
    BrowserEvent,
    DownloadProgressEvent,
    DownloadWillBeginEvent,
)

from data_plane.features.browser.application.service import BrowserService
from data_plane.features.downloads.application.exceptions import (
    DownloadNotFoundException,
)
from data_plane.features.downloads.application.models import Download
from data_plane.features.workspace.application.workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _PendingDownload:
    filename: str
    url: str


class DownloadService:
    """Collect completed files for the complete lifetime of a browser process."""

    def __init__(self, browsers: BrowserService, workspace: Workspace) -> None:
        self._browsers = browsers
        self._workspace = workspace
        self._browser_id: UUID | None = None
        self._client: Client | None = None
        self._tasks: tuple[asyncio.Task[None], ...] = ()
        self._pending: dict[str, _PendingDownload] = {}
        self._downloads: dict[str, Download] = {}

    async def start(self, browser_id: UUID) -> None:
        if self._browser_id == browser_id and self._client is not None:
            return
        await self.stop()
        cdp_url = self._browsers.upstream_cdp_url(browser_id)
        self._workspace.ensure()
        self._clear_files()
        client = Client(cdp_url)
        try:
            await client.connect()
            self._tasks = (
                asyncio.create_task(
                    self._listen_for_starts(client), name="downloads:will-begin"
                ),
                asyncio.create_task(
                    self._listen_for_progress(client), name="downloads:progress"
                ),
            )
            # Register listeners before Chrome is allowed to emit download events.
            await asyncio.sleep(0)
            await client.browser.set_download_behavior(
                behavior="allow",
                download_path=str(self._workspace.downloads),
                events_enabled=True,
            )
        except BaseException:
            for task in self._tasks:
                task.cancel()
            await client.disconnect()
            self._tasks = ()
            raise
        self._client = client
        self._browser_id = browser_id
        logger.info("Download monitoring active browser_id=%s", browser_id)

    def list(self, browser_id: UUID) -> tuple[Download, ...]:
        self._ensure_browser(browser_id)
        return tuple(self._downloads.values())

    def file(self, browser_id: UUID, download_id: str) -> Download:
        self._ensure_browser(browser_id)
        download = self._downloads.get(download_id)
        if download is None or not download.path.is_file():
            raise DownloadNotFoundException()
        return download

    async def clear(self, browser_id: UUID) -> None:
        self._ensure_browser(browser_id)
        if self._client is not None:
            await asyncio.gather(
                *(
                    self._client.browser.cancel_download(guid=guid)
                    for guid in tuple(self._pending)
                ),
                return_exceptions=True,
            )
        self._pending.clear()
        self._downloads.clear()
        self._clear_files()

    async def stop(self) -> None:
        tasks, self._tasks = self._tasks, ()
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        if self._client is not None:
            await self._client.disconnect()
        self._client = None
        self._browser_id = None
        self._pending.clear()
        self._downloads.clear()

    async def _listen_for_starts(self, client: Client) -> None:
        async for event in client.listen(
            BrowserEvent.DOWNLOAD_WILL_BEGIN, DownloadWillBeginEvent
        ):
            self._pending[event.guid] = _PendingDownload(
                filename=event.suggested_filename,
                url=event.url,
            )

    async def _listen_for_progress(self, client: Client) -> None:
        async for event in client.listen(
            BrowserEvent.DOWNLOAD_PROGRESS, DownloadProgressEvent
        ):
            if event.state == "canceled":
                self._pending.pop(event.guid, None)
            elif event.state == "completed":
                self._complete(event)

    def _complete(self, event: DownloadProgressEvent) -> None:
        pending = self._pending.pop(event.guid, None)
        if pending is None:
            logger.warning("Completed download has unknown guid=%s", event.guid)
            return
        path = (
            Path(event.file_path)
            if event.file_path
            else self._workspace.downloads / pending.filename
        )
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(self._workspace.downloads)
        except FileNotFoundError, ValueError:
            logger.warning("Completed download file is unavailable guid=%s", event.guid)
            return
        download = Download(
            id=event.guid,
            filename=resolved.name,
            url=pending.url,
            size=resolved.stat().st_size,
            path=resolved,
        )
        self._downloads[event.guid] = download
        logger.info(
            "Download completed filename=%s size=%d", download.filename, download.size
        )

    def _ensure_browser(self, browser_id: UUID) -> None:
        self._browsers.upstream_cdp_url(browser_id)
        if self._browser_id != browser_id:
            raise DownloadNotFoundException()

    def _clear_files(self) -> None:
        for path in self._workspace.downloads.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)
