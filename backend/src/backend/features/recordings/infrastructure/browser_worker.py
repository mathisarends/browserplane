import logging
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from uuid import UUID

from backend.features.browsers.application.models import Browser
from backend.features.recordings.application.exceptions import (
    RecordingAlreadyRunningException,
    RecordingNotFoundException,
    RecordingNotRunningException,
    RecordingTransferException,
)
from backend.features.recordings.application.models import (
    Recording,
    RecordingFormat,
    RecordingSegment,
    RecordingState,
)
from backend.features.recordings.application.ports import Recorder
from backend.infrastructure.browser_worker import (
    BrowserWorkerClient,
    BrowserWorkerError,
    BrowserWorkerResponseError,
)
from backend.infrastructure.bucket import Bucket, BucketObject
from generated.browser_worker import (
    GeneratedBrowserWorkerClient,
)
from generated.browser_worker import (
    RecordingResponse as WorkerRecordingResponse,
)

logger = logging.getLogger(__name__)


class BrowserWorkerRecorder(Recorder):
    def __init__(self, bucket: Bucket, client: BrowserWorkerClient) -> None:
        self._bucket = bucket
        self._client = client

    async def start(self, browser: Browser) -> Recording:
        return _to_recording(
            await self._request(
                browser,
                "start",
                lambda client: client.start_recording(browser.id),
            )
        )

    async def inspect(self, browser: Browser, recording_id: UUID) -> Recording:
        return _to_recording(
            await self._request(
                browser,
                "inspect",
                lambda client: client.inspect_recording(browser.id, recording_id),
            )
        )

    async def stop_and_store(self, browser: Browser, recording_id: UUID) -> Recording:
        recording = await self._request(
            browser,
            "stop",
            lambda client: client.stop_recording(browser.id, recording_id),
            transfer=True,
        )
        for segment in recording.segments:
            await self._store_segment(
                browser,
                recording_id,
                segment.index,
                segment.format.value,
            )
        return _to_recording(recording)

    async def _request[T](
        self,
        browser: Browser,
        action: str,
        operation: Callable[[GeneratedBrowserWorkerClient], Awaitable[T]],
        *,
        transfer: bool = False,
    ) -> T:
        try:
            return await self._client.request(
                browser.slot.browser_worker_url,
                operation,
                transfer=transfer,
            )
        except BrowserWorkerResponseError as error:
            raise _recording_error(error) from error
        except BrowserWorkerError as error:
            raise _transfer_error(action, error) from error

    async def _store_segment(
        self,
        browser: Browser,
        recording_id: UUID,
        index: int,
        extension: str,
    ) -> None:
        path = (
            f"/api/v1/browser/{browser.id}/recordings/{recording_id}"
            f"/segments/{index}/file"
        )
        try:
            async with self._client.stream(
                browser.slot.browser_worker_url,
                path,
            ) as content:
                try:
                    await self._bucket.put(
                        BucketObject(
                            key=str(
                                PurePosixPath(
                                    str(browser.id),
                                    str(recording_id),
                                    f"{index}.{extension}",
                                )
                            ),
                            content=content,
                            content_type=f"video/{extension}",
                        )
                    )
                except Exception as error:
                    raise _transfer_error("store", error) from error
        except BrowserWorkerError as error:
            raise _transfer_error("download", error) from error


def _recording_error(error: BrowserWorkerResponseError) -> Exception:
    if error.code == "recording_not_found":
        return RecordingNotFoundException()
    if error.code == "recording_already_running":
        return RecordingAlreadyRunningException()
    if error.code == "recording_not_running":
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
        segments=tuple(
            RecordingSegment(
                index=segment.index,
                target_id=segment.target_id,
                size_bytes=segment.size_bytes,
                format=RecordingFormat(segment.format.value),
                started_at=segment.started_at,
                stopped_at=segment.stopped_at,
            )
            for segment in recording.segments
        ),
    )


def _transfer_error(action: str, error: Exception) -> RecordingTransferException:
    logger.warning(
        "Could not %s browser-worker recording: %s", action, type(error).__name__
    )
    return RecordingTransferException()
