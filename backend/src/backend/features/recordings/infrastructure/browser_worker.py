import logging
from pathlib import PurePosixPath
from typing import Any, cast
from uuid import UUID

from httpx2 import AsyncClient, HTTPError
from pydantic import ValidationError

from backend.features.browsers.domain.models import Browser
from backend.features.browsers.infrastructure import routes
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
from backend.infrastructure.bucket import Bucket, BucketObject
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
        bucket: Bucket,
        http: AsyncClient,
        settings: BrowserWorkerSettings,
    ) -> None:
        self._bucket = bucket
        self._http = http
        self._settings = settings

    async def start(self, browser: Browser) -> Recording:
        try:
            recording = await self._client(browser).start_recording(browser.id)
        except ApiError as error:
            raise _recording_error(error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _transfer_error("start", error) from error
        return _to_recording(recording)

    async def inspect(self, browser: Browser, recording_id: UUID) -> Recording:
        try:
            recording = await self._client(browser).inspect_recording(
                browser.id,
                recording_id,
            )
        except ApiError as error:
            raise _recording_error(error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _transfer_error("inspect", error) from error
        return _to_recording(recording)

    async def stop_and_store(self, browser: Browser, recording_id: UUID) -> Recording:
        try:
            recording = await self._client(
                browser,
                transfer=True,
            ).stop_recording(browser.id, recording_id)
        except ApiError as error:
            raise _recording_error(error) from error
        except (HTTPError, ValidationError, ValueError) as error:
            raise _transfer_error("stop", error) from error
        await self._store_recording(browser, recording_id)
        return _to_recording(recording)

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
            url = routes.recording_file_url(browser.slot, recording_id)
            async with self._http.stream(
                "GET",
                url,
                timeout=self._settings.transfer_timeout_seconds,
            ) as response:
                response.raise_for_status()
                content = response.aiter_bytes(chunk_size=64 * 1024)
                try:
                    await self._bucket.put(
                        BucketObject(
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


def _to_recording(recording: WorkerRecordingResponse) -> Recording:
    return Recording(
        id=recording.id,
        browser_id=recording.browser_id,
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
