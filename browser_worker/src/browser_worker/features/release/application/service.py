import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

from browser_worker.features.browser.application.exceptions import (
    BrowserAlreadyRunningException,
)
from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.release.application.settings import ReleaseSettings
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.workspace.application.workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Cleanup:
    name: str
    timeout: float
    action: Callable[[], Awaitable[None]]


class WorkerReleaseService:
    """Fence and clean the worker's only browser runtime."""

    def __init__(
        self,
        browsers: BrowserService,
        downloads: DownloadService,
        recordings: RecordingService,
        screencasts: ScreencastService,
        workspace: Workspace,
        settings: ReleaseSettings,
    ) -> None:
        self._browsers = browsers
        self._downloads = downloads
        self._recordings = recordings
        self._screencasts = screencasts
        self._workspace = workspace
        self._settings = settings
        self._release_generation: int | None = None
        self._release_task: asyncio.Task[None] | None = None
        self._garbage_tasks: set[asyncio.Task[None]] = set()
        self._lock = asyncio.Lock()

    async def release(self, generation: int) -> None:
        """Join the generation's release without transferring cancellation."""
        async with self._lock:
            task = self._release_task
            if task is not None and not task.done():
                if self._release_generation != generation:
                    raise BrowserAlreadyRunningException
            else:
                cleanup_required = await self._browsers.prepare_release(generation)
                if not cleanup_required:
                    return
                task = asyncio.create_task(
                    self._release_once(generation),
                    name=f"worker-release:{generation}",
                )
                self._release_generation = generation
                self._release_task = task

        await asyncio.shield(task)

    async def _release_once(self, generation: int) -> None:
        failures: list[Exception] = []
        chromium_stopped = False
        try:
            async with asyncio.timeout(self._settings.total_timeout):
                cleanups = (
                    Cleanup(
                        "recordings",
                        self._settings.recording_timeout,
                        self._recordings.release,
                    ),
                    Cleanup(
                        "downloads",
                        self._settings.downloads_timeout,
                        self._downloads.stop,
                    ),
                    Cleanup(
                        "screencast",
                        self._settings.screencast_timeout,
                        self._screencasts.release,
                    ),
                )
                results = await asyncio.gather(
                    *(self._run_cleanup(cleanup) for cleanup in cleanups)
                )
                failures.extend(error for error in results if error is not None)

                chromium_error = await self._run_cleanup(
                    Cleanup(
                        "chromium",
                        self._settings.chromium_timeout,
                        self._browsers.stop_process,
                    )
                )
                if chromium_error is not None:
                    failures.append(chromium_error)
                else:
                    chromium_stopped = True

                isolated: Path | None = None
                try:
                    async with asyncio.timeout(self._settings.workspace_timeout):
                        isolated = await asyncio.to_thread(self._workspace.isolate)
                except Exception as error:
                    logger.exception("Worker release failed for workspace")
                    failures.append(error)
                if isolated is not None:
                    self._delete_in_background(isolated)
        except Exception as error:
            logger.exception("Worker release exceeded its total budget")
            failures.append(error)

        if not chromium_stopped:
            chromium_error = await self._run_cleanup(
                Cleanup(
                    "chromium",
                    self._settings.chromium_timeout,
                    self._browsers.stop_process,
                )
            )
            if chromium_error is not None:
                failures.append(chromium_error)

        succeeded = not failures and self._postconditions_hold()
        await self._browsers.finish_release(generation, succeeded=succeeded)
        if not succeeded:
            if not failures:
                failures.append(RuntimeError("Release postconditions were not met"))
            raise ExceptionGroup("Worker release was incomplete", failures)

    async def _run_cleanup(self, cleanup: Cleanup) -> Exception | None:
        try:
            async with asyncio.timeout(cleanup.timeout):
                await cleanup.action()
        except Exception as error:
            logger.exception("Worker release failed for %s", cleanup.name)
            return error
        return None

    def _postconditions_hold(self) -> bool:
        return (
            self._recordings.is_idle
            and self._downloads.is_idle
            and self._screencasts.is_idle
            and not any(path.exists() for path in self._workspace.directories)
        )

    def _delete_in_background(self, directory: Path) -> None:
        task = asyncio.create_task(
            asyncio.to_thread(self._workspace.delete_isolated, directory),
            name=f"workspace-garbage:{directory.name}",
        )
        self._garbage_tasks.add(task)
        task.add_done_callback(self._garbage_deleted)

    def _garbage_deleted(self, task: asyncio.Task[None]) -> None:
        self._garbage_tasks.discard(task)
        try:
            task.result()
        except BaseException:
            logger.exception("Could not delete isolated worker workspace")
