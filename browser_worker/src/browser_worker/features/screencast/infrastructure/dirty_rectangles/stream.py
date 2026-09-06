import asyncio
import logging
import queue
import threading
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager, suppress

from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.features.screencast.infrastructure.settings import (
    DirtyRectangleSettings,
)
from browser_worker.shared.tasks import cancel_and_wait

from .encoder import encode_update
from .models import EncodedUpdate, RgbFrame

logger = logging.getLogger(__name__)

_STREAM_ENDED = object()
type _Update = EncodedUpdate | Exception | object


class DirtyRectangleJpegStream:
    """Adapt complete image frames to packets containing changed JPEG tiles.

    Diff state belongs to a subscription, so every new consumer starts with a
    complete canvas even when the wrapped source stream is shared.
    """

    def __init__(
        self,
        source: FrameStream,
        settings: DirtyRectangleSettings,
    ) -> None:
        self._source = source
        self._settings = settings

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[AsyncIterator[bytes]]:
        async with self._source.subscribe() as frames:
            yield _EncoderPipeline(frames, self._settings).packets()

    async def close(self) -> None:
        """Close the wrapped frame stream."""
        await self._source.close()


class _EncoderPipeline:
    """Turn one subscription's frames into packets on a worker thread.

    Encoding costs more than the browser's gap between frames, so the pipeline
    holds exactly two things back: the frame queue keeps only the newest frame,
    and the encoder picks up the next one only once the consumer has taken the
    previous packet. A slow consumer therefore skips frames instead of building
    a backlog of stale ones.
    """

    _POLL_INTERVAL = 0.05
    _THREAD_STOP_TIMEOUT = 2

    def __init__(
        self, frames: AsyncIterator[bytes], settings: DirtyRectangleSettings
    ) -> None:
        self._frames = frames
        self._settings = settings
        self._loop = asyncio.get_running_loop()
        self._pending: queue.Queue[bytes] = queue.Queue(maxsize=1)
        self._updates: asyncio.Queue[_Update] = asyncio.Queue(maxsize=1)
        self._free_slot = threading.Semaphore(1)
        self._frames_done = threading.Event()
        self._frames_error: Exception | None = None
        self._stopped = threading.Event()

    async def packets(self) -> AsyncIterator[bytes]:
        """Yield one packet per encoded update until the frames run out."""
        encoder = threading.Thread(
            target=self._encode_frames,
            name="screencast:dirty-jpeg-encoder",
            daemon=True,
        )
        encoder.start()
        reader = asyncio.create_task(
            self._read_frames(), name="screencast:dirty-jpeg-input"
        )
        try:
            while True:
                update = await self._updates.get()
                if update is _STREAM_ENDED:
                    self._free_slot.release()
                    return
                if isinstance(update, Exception):
                    self._free_slot.release()
                    raise update
                assert isinstance(update, EncodedUpdate)
                _log_update(update)
                try:
                    yield update.packet
                finally:
                    self._free_slot.release()
        finally:
            self._stopped.set()
            await cancel_and_wait(reader)
            await self._join(encoder)

    async def _read_frames(self) -> None:
        try:
            async for frame in self._frames:
                self._offer(frame)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._frames_error = error
        finally:
            self._frames_done.set()

    def _offer(self, frame: bytes) -> None:
        """Queue a frame, dropping the one the encoder has not picked up yet."""
        try:
            self._pending.put_nowait(frame)
        except queue.Full:
            with suppress(queue.Empty):
                self._pending.get_nowait()
            self._pending.put_nowait(frame)

    def _encode_frames(self) -> None:
        """Encode frames on the worker thread until the stream ends or fails."""
        previous: RgbFrame | None = None
        while self._acquire_slot():
            frame = self._next_frame()
            if frame is None:
                if not self._frames_done.is_set():
                    self._free_slot.release()
                    continue
                self._publish(self._frames_error or _STREAM_ENDED)
                return
            try:
                previous, packet, metrics = encode_update(
                    frame, previous, self._settings
                )
            except Exception as error:
                self._publish(error)
                return
            if packet is None:
                # Nothing changed, so there is nothing to send and the consumer
                # keeps waiting on the slot it never got to use.
                self._free_slot.release()
                continue
            self._publish(EncodedUpdate(packet, metrics))

    def _acquire_slot(self) -> bool:
        """Wait for the consumer to take the previous packet, unless stopped."""
        while not self._stopped.is_set():
            if self._free_slot.acquire(timeout=self._POLL_INTERVAL):
                return True
        return False

    def _next_frame(self) -> bytes | None:
        try:
            return self._pending.get(timeout=self._POLL_INTERVAL)
        except queue.Empty:
            return None

    def _publish(self, update: _Update) -> None:
        with suppress(RuntimeError):
            self._loop.call_soon_threadsafe(self._updates.put_nowait, update)

    async def _join(self, encoder: threading.Thread) -> None:
        deadline = self._loop.time() + self._THREAD_STOP_TIMEOUT
        while encoder.is_alive() and self._loop.time() < deadline:
            await asyncio.sleep(0.01)
        if encoder.is_alive():
            logger.warning(
                "Dirty JPEG encoder thread did not stop within %d seconds",
                self._THREAD_STOP_TIMEOUT,
            )


def _log_update(update: EncodedUpdate) -> None:
    logger.debug(
        "Dirty JPEG frame decode=%.2fms diff=%.2fms encode=%.2fms "
        "dirty=%.1f%% patches=%d payload=%dB",
        update.metrics.decode_ms,
        update.metrics.diff_ms,
        update.metrics.encode_ms,
        update.metrics.dirty_ratio * 100,
        update.metrics.patches,
        len(update.packet),
    )
