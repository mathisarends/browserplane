import logging
from pathlib import PurePosixPath
from uuid import UUID

from httpx2 import AsyncClient

from backend.features.browsers.application.models import Browser
from backend.features.recordings.application.exceptions import (
    RecordingAlreadyRunningException,
    RecordingNotFoundException,
    RecordingNotRunningException,
    RecordingTransferException,
)
from backend.features.recordings.application.ports import RecordingGateway
from backend.infrastructure.bucket import Bucket, BucketObject
from backend.request_logging import current_request_id
from generated.browser_worker import (
    ApiError,
    GeneratedBrowserWorkerClient,
    RecordingResponse,
)

logger = logging.getLogger(__name__)
_TRANSFER_TIMEOUT_SECONDS = 3600.0


def _request_headers() -> dict[str, str] | None:
    request_id = current_request_id()
    return {"X-Request-ID": request_id} if request_id is not None else None


class BrowserWorkerRecordingGateway(RecordingGateway):
    def __init__(self, bucket: Bucket) -> None:
        self._bucket = bucket

    async def start(self, browser: Browser) -> RecordingResponse:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedBrowserWorkerClient(
                    http, browser.slot.browser_worker_url
                )
                return await client.start_recording(browser.id)
        except ApiError as error:
            raise _recording_error(error) from error
        except Exception as error:
            raise _transfer_error("start", error) from error

    async def inspect(self, browser: Browser, recording_id: UUID) -> RecordingResponse:
        try:
            async with AsyncClient(headers=_request_headers()) as http:
                client = GeneratedBrowserWorkerClient(
                    http, browser.slot.browser_worker_url
                )
                return await client.inspect_recording(browser.id, recording_id)
        except ApiError as error:
            raise _recording_error(error) from error
        except Exception as error:
            raise _transfer_error("inspect", error) from error

    async def stop_and_store(
        self, browser: Browser, recording_id: UUID
    ) -> RecordingResponse:
        try:
            async with AsyncClient(
                headers=_request_headers(), timeout=_TRANSFER_TIMEOUT_SECONDS
            ) as http:
                client = GeneratedBrowserWorkerClient(
                    http,
                    browser.slot.browser_worker_url,
                    timeout=_TRANSFER_TIMEOUT_SECONDS,
                )
                recording = await client.stop_recording(browser.id, recording_id)
                for segment in recording.segments:
                    await self._store_segment(
                        http,
                        browser,
                        recording_id,
                        segment.index,
                        segment.format.value,
                    )
                return recording
        except ApiError as error:
            raise _recording_error(error) from error
        except Exception as error:
            raise _transfer_error("stop and store", error) from error

    async def _store_segment(
        self,
        http: AsyncClient,
        browser: Browser,
        recording_id: UUID,
        index: int,
        extension: str,
    ) -> None:
        path = (
            f"/api/v1/browser/{browser.id}/recordings/{recording_id}"
            f"/segments/{index}/file"
        )
        url = f"{browser.slot.browser_worker_url.rstrip('/')}{path}"
        async with http.stream("GET", url) as response:
            response.raise_for_status()
            await self._bucket.put(
                BucketObject(
                    key=str(
                        PurePosixPath(
                            str(browser.id),
                            str(recording_id),
                            f"{index}.{extension}",
                        )
                    ),
                    content=response.aiter_bytes(chunk_size=64 * 1024),
                    content_type=f"video/{extension}",
                )
            )


def _recording_error(error: ApiError) -> Exception:
    code = getattr(error.parsed_body, "code", None)
    if code == "recording_not_found":
        return RecordingNotFoundException()
    if code == "recording_already_running":
        return RecordingAlreadyRunningException()
    if code == "recording_not_running":
        return RecordingNotRunningException()
    return _transfer_error("communicate with", error)


def _transfer_error(action: str, error: Exception) -> RecordingTransferException:
    logger.warning(
        "Could not %s browser-worker recording: %s", action, type(error).__name__
    )
    return RecordingTransferException()
