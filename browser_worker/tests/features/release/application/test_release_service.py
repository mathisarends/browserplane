from pathlib import Path
from typing import cast
from uuid import uuid4

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
from browser_worker.features.screencast.application.service import ScreencastService
from browser_worker.features.workspace.application.workspace import Workspace


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
    )
    await browsers.create(uuid4())

    await release.release()
    await release.release()

    assert process.stop_count == 1
    assert not any(path.exists() for path in workspace.directories)
    with pytest.raises(BrowserNotFoundException):
        browsers.get()
