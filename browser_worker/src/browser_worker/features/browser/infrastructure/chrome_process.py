import asyncio
import os
import shutil
import signal
import subprocess
import tempfile
import time
from contextlib import suppress
from pathlib import Path

from browser_worker.features.browser.application.exceptions import (
    BrowserStartupException,
)
from browser_worker.features.browser.application.ports import BrowserProcess
from browser_worker.features.browser.infrastructure.settings import BrowserSettings


class ChromeProcess(BrowserProcess):
    """Own one Chromium process and its temporary profile."""

    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._process: asyncio.subprocess.Process | None = None
        self._profile: tempfile.TemporaryDirectory[str] | None = None

    def is_available(self) -> bool:
        return _find_executable(self._settings) is not None

    async def start(self) -> str:
        executable = self._require_executable()
        self._profile = tempfile.TemporaryDirectory(prefix="browser-worker-")
        profile_path = Path(self._profile.name)
        args = [
            executable,
            "--remote-debugging-port=0",
            f"--user-data-dir={profile_path}",
            f"--window-size={self._settings.width},{self._settings.height}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-dev-shm-usage",
            "--no-sandbox",
        ]
        if self._settings.headless:
            args.append("--headless=new")
        args.append("about:blank")
        creation_flags = (
            subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            if subprocess._mswindows
            else 0
        )
        self._process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=creation_flags,
            start_new_session=not subprocess._mswindows,
        )
        try:
            return await self._wait_for_cdp_endpoint(profile_path)
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        process = self._process
        failures: list[Exception] = []
        if process is not None and process.returncode is None:
            try:
                await _stop_process_tree(process)
            except Exception as error:
                failures.append(error)
        if process is None or process.returncode is not None:
            self._process = None
        profile = self._profile
        if profile is not None:
            # Keep the handle when cleanup fails so an idempotent retry can try
            # removing the same profile again.
            try:
                profile.cleanup()
            except Exception as error:
                failures.append(error)
            else:
                self._profile = None
        if failures:
            raise ExceptionGroup("Could not fully stop Chromium", failures)

    async def _wait_for_cdp_endpoint(self, profile_path: Path) -> str:
        active_port = profile_path / "DevToolsActivePort"
        deadline = time.monotonic() + self._settings.startup_timeout
        while time.monotonic() < deadline:
            if self._process is None or self._process.returncode is not None:
                raise BrowserStartupException("Chromium exited during startup")
            if active_port.exists():
                lines = active_port.read_text(encoding="utf-8").splitlines()
                if len(lines) >= 2:
                    return f"ws://127.0.0.1:{lines[0]}{lines[1]}"
            await asyncio.sleep(0.05)
        raise BrowserStartupException("Timed out waiting for Chromium's CDP endpoint")

    def _require_executable(self) -> str:
        executable = _find_executable(self._settings)
        if executable is None:
            raise BrowserStartupException(
                "No Chromium browser found; set BROWSER_WORKER_EXECUTABLE"
            )
        return executable


def _find_executable(settings: BrowserSettings) -> str | None:
    if settings.executable is not None:
        return shutil.which(settings.executable)

    candidates = (
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("chrome"),
        shutil.which("msedge"),
        _first_existing(
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ),
    )
    return next((candidate for candidate in candidates if candidate is not None), None)


def _first_existing(*paths: Path) -> str | None:
    return next((str(path) for path in paths if path.is_file()), None)


async def _stop_process_tree(process: asyncio.subprocess.Process) -> None:
    if subprocess._mswindows:
        await _stop_windows_process_tree(process)
        return
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except TimeoutError:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        await process.wait()


async def _stop_windows_process_tree(process: asyncio.subprocess.Process) -> None:
    taskkill = await asyncio.create_subprocess_exec(
        "taskkill.exe",
        "/PID",
        str(process.pid),
        "/T",
        "/F",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    await taskkill.wait()
    if process.returncode is None:
        process.kill()
    await process.wait()
