import logging
from pathlib import PurePosixPath
from typing import Any, cast
from uuid import UUID

from httpx2 import AsyncClient, HTTPError
from pydantic import ValidationError

from backend.features.browsers.domain.models import Browser
from backend.features.browsers.infrastructure.routes import BrowserWorkerRoutes
from backend.features.recordings.application.exceptions import (
    RecordingAlreadyExistsException,
    RecordingNotFoundException,
    RecordingNotRunningException,
    RecordingTransferException,
)
from backend.features.recordings.application.models import (
    Recording,
    RecordingState,
)
from backend.features.recordings.application.ports import Recorder
from backend.infrastructure.browser_worker.settings import BrowserWorkerSettings
from backend.infrastructure.storage import ObjectStorage, StoredObject
from generated.browser_worker import (
    ApiError,
    GeneratedBrowserWorkerClient,
)
from generated.browser_worker import (
    RecordingResponse as WorkerRecordingResponse,
)

logger = logging.getLogger(__name__)


class BrowserWorkerRecorder(Recorder):
    def __init__(
        self,
        storage: ObjectStorage,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
        routes: BrowserWorkerRoutes,
    ) -> None:
        self._storage = storage
        self._http = http
        self._settings = settings
        self._routes = routes

    async def start(self, browser: Browser) -> Recording:
        try:
            client = self._client(browser)
            recording = await client.start_recording()
        except ApiError as error:
            raise _recording_error(error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _transfer_error("start", error) from error
        return _to_recording(recording, browser_id=browser.id)

    async def inspect(self, browser: Browser, recording_id: UUID) -> Recording:
        try:
            client = self._client(browser)
            recording = await client.inspect_recording(recording_id)
        except ApiError as error:
            raise _recording_error(error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _transfer_error("inspect", error) from error
        return _to_recording(recording, browser_id=browser.id)

    async def stop_and_store(self, browser: Browser, recording_id: UUID) -> Recording:
        try:
            client = self._client(
                browser,
                transfer=True,
            )
            recording = await client.stop_recording(recording_id)
        except ApiError as error:
            raise _recording_error(error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _transfer_error("stop", error) from error
        await self._store_recording(browser, recording_id)
        return _to_recording(recording, browser_id=browser.id)

    async def file(self, browser: Browser, recording_id: UUID) -> bytes:
        """Fetch the completed video while its browser worker still owns it."""
        try:
            response = await self._http.get(
                self._routes.recording_file_url(browser.slot, recording_id),
                timeout=self._settings.transfer_timeout_seconds,
            )
            response.raise_for_status()
            return response.content
        except HTTPError as error:
            response = getattr(error, "response", None)
            if response is not None and response.status_code == 404:
                raise RecordingNotFoundException() from error
            raise _transfer_error("download", error) from error

    def _client(
        self,
        browser: Browser,
        *,
        transfer: bool = False,
    ) -> GeneratedBrowserWorkerClient:
        timeout = (
            self._settings.transfer_timeout_seconds
            if transfer
            else self._settings.request_timeout_seconds
        )
        return GeneratedBrowserWorkerClient(
            cast(Any, self._http),
            browser.slot.browser_worker_url,
            timeout=timeout,
        )

    async def _store_recording(
        self,
        browser: Browser,
        recording_id: UUID,
    ) -> None:
        try:
            url = self._routes.recording_file_url(browser.slot, recording_id)
            async with self._http.stream(
                "GET",
                url,
                timeout=self._settings.transfer_timeout_seconds,
            ) as response:
                response.raise_for_status()
                content = response.aiter_bytes(chunk_size=64 * 1024)
                try:
                    await self._storage.put(
                        StoredObject(
                            key=str(
                                PurePosixPath(
                                    str(browser.id),
                                    str(recording_id),
                                    "video.mp4",
                                )
                            ),
                            content=content,
                            content_type=response.headers.get(
                                "content-type", "video/mp4"
                            ),
                        )
                    )
                except Exception as error:
                    raise _transfer_error("store", error) from error
        except HTTPError as error:
            raise _transfer_error("download", error) from error


def _recording_error(error: ApiError) -> Exception:
    code = getattr(error.parsed_body, "code", None)
    if code == "recording_not_found":
        return RecordingNotFoundException()
    if code == "recording_already_exists":
        return RecordingAlreadyExistsException()
    if code == "recording_not_running":
        return RecordingNotRunningException()
    return _transfer_error("communicate with", error)


def _to_recording(
    recording: WorkerRecordingResponse,
    *,
    browser_id: UUID,
) -> Recording:
    return Recording(
        id=recording.id,
        browser_id=browser_id,
        state=RecordingState(recording.state.value),
        started_at=recording.started_at,
        stopped_at=recording.stopped_at,
        size_bytes=recording.size_bytes,
    )


def _transfer_error(action: str, error: Exception) -> RecordingTransferException:
    logger.warning(
        "Could not %s browser-worker recording: %s", action, type(error).__name__
    )
    return RecordingTransferException()
