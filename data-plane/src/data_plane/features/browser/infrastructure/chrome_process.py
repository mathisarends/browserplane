import asyncio
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from data_plane.features.browser.application.exceptions import BrowserStartupException
from data_plane.features.browser.application.ports import BrowserProcess
from data_plane.features.browser.infrastructure.settings import BrowserSettings


class ChromeProcess(BrowserProcess):
    """Own one Chromium process and its temporary profile."""

    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._process: asyncio.subprocess.Process | None = None
        self._profile: tempfile.TemporaryDirectory[str] | None = None

    @staticmethod
    def is_available(settings: BrowserSettings) -> bool:
        return _find_executable(settings) is not None

    async def start(self) -> str:
        executable = self._find_executable()
        self._profile = tempfile.TemporaryDirectory(
            prefix="data-plane-", ignore_cleanup_errors=True
        )
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
        creation_flags = subprocess.CREATE_NO_WINDOW if subprocess._mswindows else 0
        self._process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        try:
            return await self._wait_for_cdp_endpoint(profile_path)
        except BaseException:
            await self.stop()
            raise

    async def stop(self) -> None:
        if self._process is not None and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
        self._process = None
        if self._profile is not None:
            self._profile.cleanup()
            self._profile = None

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

    def _find_executable(self) -> str:
        executable = _find_executable(self._settings)
        if executable is None:
            raise BrowserStartupException(
                "No Chromium browser found; set DATA_PLANE_EXECUTABLE"
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
