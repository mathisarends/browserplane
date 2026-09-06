import asyncio
from pathlib import Path
from typing import cast

import pytest
from tests.fakes import FakeBrowserProcess, FakeFrameStream

from browser_worker.features.browser.application.exceptions import (
    BrowserNotFoundException,
)
from browser_worker.features.browser.application.service import BrowserService
from browser_worker.features.downloads.application.service import DownloadService
from browser_worker.features.recordings.application.ports import ScreenRecorder
from browser_worker.features.recordings.application.service import RecordingService
from browser_worker.features.release.application.service import WorkerReleaseService
from browser_worker.features.release.application.settings import ReleaseSettings
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.workspace.application.workspace import Workspace


class BlockingBrowserProcess(FakeBrowserProcess):
    def __init__(self) -> None:
        super().__init__()
        self.stop_started = asyncio.Event()
        self.allow_stop = asyncio.Event()

    async def stop(self) -> None:
        self.stop_count += 1
        self.stop_started.set()
        await self.allow_stop.wait()


@pytest.mark.asyncio
async def test_release_returns_worker_to_its_empty_initial_state(
    tmp_path: Path,
) -> None:
    process = FakeBrowserProcess()
    browsers = BrowserService(process)
    workspace = Workspace(tmp_path / "workspace")
    workspace.ensure()
    for directory in workspace.directories:
        (directory / "owned-file").write_text("worker state", encoding="utf-8")
    downloads = DownloadService(browsers, workspace)
    recordings = RecordingService(
        browsers,
        workspace,
        lambda _: cast(ScreenRecorder, object()),
    )
    screencasts = ScreencastService(lambda _: FakeFrameStream())
    release = WorkerReleaseService(
        browsers,
        downloads,
        recordings,
        screencasts,
        workspace,
        ReleaseSettings(),
    )
    await browsers.create(7)

    await release.release(7)
    await release.release(7)

    assert process.stop_count == 1
    assert not any(path.exists() for path in workspace.directories)
    with pytest.raises(BrowserNotFoundException):
        browsers.inspect()


@pytest.mark.asyncio
async def test_release_is_shared_and_shielded_from_caller_cancellation(
    tmp_path: Path,
) -> None:
    process = BlockingBrowserProcess()
    browsers = BrowserService(process)
    workspace = Workspace(tmp_path / "workspace")
    release = WorkerReleaseService(
        browsers,
        DownloadService(browsers, workspace),
        RecordingService(
            browsers,
            workspace,
            lambda _: cast(ScreenRecorder, object()),
        ),
        ScreencastService(lambda _: FakeFrameStream()),
        workspace,
        ReleaseSettings(),
    )
    await browsers.create(7)

    first_caller = asyncio.create_task(release.release(7))
    await process.stop_started.wait()
    second_caller = asyncio.create_task(release.release(7))
    first_caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_caller

    process.allow_stop.set()
    await second_caller
    assert process.stop_count == 1
