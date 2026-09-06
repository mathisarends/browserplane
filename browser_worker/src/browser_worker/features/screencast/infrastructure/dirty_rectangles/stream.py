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

from .encoder import encode_update
from .models import EncodedUpdate, RgbFrame

logger = logging.getLogger(__name__)

_STREAM_ENDED = object()


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
            yield self._packets(frames)

    async def close(self) -> None:
        """Close the wrapped frame stream."""
        await self._source.close()

    async def _packets(self, frames: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        loop = asyncio.get_running_loop()
        input_queue: queue.Queue[bytes] = queue.Queue(maxsize=1)
        output_queue: asyncio.Queue[EncodedUpdate | Exception | object] = asyncio.Queue(
            maxsize=1
        )
        producer_done = threading.Event()
        stop = threading.Event()
        output_slot = threading.Semaphore(1)
        producer_error: list[Exception] = []
        worker = threading.Thread(
            target=_encoder_worker,
            args=(
                input_queue,
                output_queue,
                loop,
                output_slot,
                producer_done,
                producer_error,
                stop,
                self._settings,
            ),
            name="screencast:dirty-jpeg-encoder",
            daemon=True,
        )
        worker.start()
        producer = asyncio.create_task(
            _produce_latest_frames(
                frames,
                input_queue,
                producer_done,
                producer_error,
            ),
            name="screencast:dirty-jpeg-input",
        )
        try:
            while True:
                item = await output_queue.get()
                if item is _STREAM_ENDED:
                    output_slot.release()
                    return
                if isinstance(item, Exception):
                    output_slot.release()
                    raise item
                assert isinstance(item, EncodedUpdate)
                logger.debug(
                    "Dirty JPEG frame decode=%.2fms diff=%.2fms encode=%.2fms "
                    "dirty=%.1f%% payload=%dB",
                    item.metrics.decode_ms,
                    item.metrics.diff_ms,
                    item.metrics.encode_ms,
                    item.metrics.dirty_ratio * 100,
                    len(item.packet),
                )
                try:
                    yield item.packet
                finally:
                    output_slot.release()
        finally:
            stop.set()
            producer.cancel()
            await asyncio.gather(producer, return_exceptions=True)
            await _wait_for_thread(worker)


async def _produce_latest_frames(
    frames: AsyncIterator[bytes],
    input_queue: queue.Queue[bytes],
    done: threading.Event,
    errors: list[Exception],
) -> None:
    try:
        async for frame in frames:
            _put_latest_frame(input_queue, frame)
    except asyncio.CancelledError:
        raise
    except Exception as error:
        errors.append(error)
    finally:
        done.set()


def _put_latest_frame(input_queue: queue.Queue[bytes], frame: bytes) -> None:
    try:
        input_queue.put_nowait(frame)
        return
    except queue.Full:
        pass
    with suppress(queue.Empty):
        input_queue.get_nowait()
    input_queue.put_nowait(frame)


def _encoder_worker(
    input_queue: queue.Queue[bytes],
    output_queue: asyncio.Queue[EncodedUpdate | Exception | object],
    loop: asyncio.AbstractEventLoop,
    output_slot: threading.Semaphore,
    producer_done: threading.Event,
    producer_error: list[Exception],
    stop: threading.Event,
    settings: DirtyRectangleSettings,
) -> None:
    previous: RgbFrame | None = None
    while _acquire_output_slot(output_slot, stop):
        try:
            frame = input_queue.get(timeout=0.05)
        except queue.Empty:
            if not producer_done.is_set():
                output_slot.release()
                continue
            terminal = producer_error[0] if producer_error else _STREAM_ENDED
            _send_to_event_loop(loop, output_queue, terminal)
            return

        try:
            previous, packet, metrics = encode_update(frame, previous, settings)
        except Exception as error:
            _send_to_event_loop(loop, output_queue, error)
            return
        if packet is None:
            output_slot.release()
            continue
        _send_to_event_loop(loop, output_queue, EncodedUpdate(packet, metrics))


def _acquire_output_slot(
    output_slot: threading.Semaphore,
    stop: threading.Event,
) -> bool:
    while not stop.is_set():
        if output_slot.acquire(timeout=0.05):
            return True
    return False


def _send_to_event_loop(
    loop: asyncio.AbstractEventLoop,
    output_queue: asyncio.Queue[EncodedUpdate | Exception | object],
    item: EncodedUpdate | Exception | object,
) -> None:
    with suppress(RuntimeError):
        loop.call_soon_threadsafe(output_queue.put_nowait, item)


async def _wait_for_thread(worker: threading.Thread) -> None:
    deadline = asyncio.get_running_loop().time() + 2
    while worker.is_alive() and asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.01)
    if worker.is_alive():
        logger.warning("Dirty JPEG encoder thread did not stop within two seconds")
