import asyncio
from pathlib import Path
from typing import cast

import pytest
from tests.fakes import FakeBrowserProcess, FakeFrameStream

from browser_worker.features.browser.application import (
    BrowserNotFoundException,
    BrowserService,
)
from browser_worker.features.downloads.application import DownloadService
from browser_worker.features.downloads.infrastructure.cdp import CdpDownloadStore
from browser_worker.features.recordings.application import (
    RecordingService,
    ScreenRecorder,
)
from browser_worker.features.release.application import (
    ReleaseSettings,
    WorkerReleaseService,
)
from browser_worker.features.screencast.application import ScreencastService
from browser_worker.features.workspace.infrastructure.filesystem import (
    FilesystemWorkspace,
)


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
    workspace = FilesystemWorkspace(tmp_path / "workspace")
    workspace.ensure()
    for directory in workspace.directories:
        (directory / "owned-file").write_text("worker state", encoding="utf-8")
    downloads = DownloadService(browsers, CdpDownloadStore(workspace))
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
    workspace = FilesystemWorkspace(tmp_path / "workspace")
    release = WorkerReleaseService(
        browsers,
        DownloadService(browsers, CdpDownloadStore(workspace)),
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
    await asyncio.wait_for(process.stop_started.wait(), timeout=2)
    second_caller = asyncio.create_task(release.release(7))
    first_caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(first_caller, timeout=2)

    process.allow_stop.set()
    await asyncio.wait_for(second_caller, timeout=2)
    assert process.stop_count == 1
