import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.workspace.application.workspace import Workspace

logger = logging.getLogger(__name__)

type Cleanup = tuple[str, Callable[[], Awaitable[None]]]


class WorkerReleaseService:
    """Return every worker-owned runtime resource to its initial state."""

    def __init__(
        self,
        browsers: BrowserService,
        downloads: DownloadService,
        recordings: RecordingService,
        screencasts: ScreencastService,
        workspace: Workspace,
    ) -> None:
        self._browsers = browsers
        self._downloads = downloads
        self._recordings = recordings
        self._screencasts = screencasts
        self._workspace = workspace
        self._lock = asyncio.Lock()

    async def release(
        self,
        browser_id: UUID | None = None,
        generation: int | None = None,
    ) -> None:
        """Release all resources, attempting every step even after a failure."""
        async with self._lock:
            failures: list[Exception] = []
            cleanups: tuple[Cleanup, ...] = (
                ("recordings", self._recordings.release),
                ("downloads", self._downloads.stop),
                ("screencast", self._screencasts.release),
            )
            # The browser scope removes its public identity immediately and keeps
            # creation blocked until every worker-owned resource has been cleared.
            try:
                async with self._browsers.release_scope(browser_id, generation):
                    for resource, cleanup in cleanups:
                        try:
                            await cleanup()
                        except Exception as error:
                            logger.exception("Worker release failed for %s", resource)
                            failures.append(error)
                    try:
                        self._workspace.clear()
                    except Exception as error:
                        logger.exception("Worker release failed for workspace")
                        failures.append(error)
            except Exception as error:
                logger.exception("Worker release failed for browser")
                failures.append(error)
            if failures:
                raise ExceptionGroup("Worker release was incomplete", failures)
