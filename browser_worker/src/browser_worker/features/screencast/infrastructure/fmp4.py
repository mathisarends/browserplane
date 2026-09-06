import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator, AsyncIterator

from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.shared.tasks import cancel_and_wait

logger = logging.getLogger(__name__)

_NOMINAL_FPS = 30
_MOOF_BOX_TYPE = b"moof"
_MDAT_BOX_TYPE = b"mdat"
_STREAM_ENDED = object()


class Fmp4Livestream:
    """Encode incoming JPEG frames into a low-latency fragmented MP4 stream."""

    KEYFRAME_INTERVAL_SECONDS = 1
    _SUBSCRIBER_QUEUE_SIZE = 10
    _FRAME_QUEUE_SIZE = 2

    def __init__(self) -> None:
        self._process: asyncio.subprocess.Process | None = None
        self._subscribers: set[asyncio.Queue[bytes | object]] = set()
        self._frame_queue: asyncio.Queue[bytes] = asyncio.Queue(
            maxsize=self._FRAME_QUEUE_SIZE
        )
        self._reader_task: asyncio.Task[None] | None = None
        self._writer_task: asyncio.Task[None] | None = None

        self._cached_init_segment = b""
        self._is_finding_init = True
        self._init_boxes: list[bytes] = []
        self._fragment_boxes: list[bytes] = []

    @contextlib.asynccontextmanager
    async def stream(self) -> AsyncGenerator[AsyncGenerator[bytes]]:
        queue: asyncio.Queue[bytes | object] = asyncio.Queue(
            maxsize=self._SUBSCRIBER_QUEUE_SIZE
        )
        self._subscribers.add(queue)
        if self._cached_init_segment:
            queue.put_nowait(self._cached_init_segment)
        try:
            yield self._chunks(queue)
        finally:
            self._subscribers.discard(queue)

    async def _chunks(
        self, queue: asyncio.Queue[bytes | object]
    ) -> AsyncGenerator[bytes]:
        while True:
            chunk = await queue.get()
            if chunk is _STREAM_ENDED:
                return
            assert isinstance(chunk, bytes)
            yield chunk

    async def start(self) -> None:
        if self._process is not None:
            return

        self._reset_encoding_state()
        self._process = await asyncio.create_subprocess_exec(
            *_build_ffmpeg_command(self.KEYFRAME_INTERVAL_SECONDS),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if self._process.stdout is None or self._process.stdin is None:
            await self.stop()
            raise RuntimeError("Failed to start fMP4 livestream: ffmpeg pipes missing")

        self._writer_task = asyncio.create_task(
            self._write_frames(), name="screencast:fmp4-writer"
        )
        self._reader_task = asyncio.create_task(
            self._read_boxes(), name="screencast:fmp4-reader"
        )

    async def publish_frame(self, frame_data: bytes) -> None:
        if self._process is None or not self._subscribers:
            return
        if self._frame_queue.full():
            self._frame_queue.get_nowait()
        self._frame_queue.put_nowait(frame_data)

    async def _write_frames(self) -> None:
        while True:
            frame_data = await self._frame_queue.get()
            if not await self._write_frame_to_stdin(frame_data):
                return

    async def _write_frame_to_stdin(self, frame_data: bytes) -> bool:
        if self._process is None or self._process.stdin is None:
            return False
        try:
            self._process.stdin.write(frame_data)
            await self._process.stdin.drain()
        except BrokenPipeError, ConnectionResetError:
            logger.error("fMP4 livestream ffmpeg pipe broke")
            return False
        return True

    async def _read_boxes(self) -> None:
        try:
            while self._process is not None and self._process.stdout is not None:
                box = await self._read_box()
                if box is None:
                    break
                self._consume_box(box)
            if self._fragment_boxes:
                logger.warning("Discarding incomplete fMP4 fragment at end of stream")
                self._fragment_boxes.clear()
        finally:
            self._end_subscribers()

    def _consume_box(self, box: bytes) -> None:
        box_type = _box_type(box)
        if self._is_finding_init:
            if box_type != _MOOF_BOX_TYPE:
                self._init_boxes.append(box)
                return
            self._cache_and_publish_init_segment()
            self._fragment_boxes = [box]
            return

        if box_type == _MOOF_BOX_TYPE:
            if self._fragment_boxes:
                logger.warning("Discarding incomplete fMP4 fragment before next moof")
            self._fragment_boxes = [box]
            return
        if not self._fragment_boxes:
            return

        self._fragment_boxes.append(box)
        if box_type == _MDAT_BOX_TYPE:
            fragment = b"".join(self._fragment_boxes)
            self._fragment_boxes.clear()
            self._publish_fragment(fragment)

    def _cache_and_publish_init_segment(self) -> None:
        self._cached_init_segment = b"".join(self._init_boxes)
        self._init_boxes.clear()
        self._is_finding_init = False
        logger.info(
            "Cached MP4 init segment (%d bytes)", len(self._cached_init_segment)
        )
        for queue in tuple(self._subscribers):
            queue.put_nowait(self._cached_init_segment)

    def _publish_fragment(self, fragment: bytes) -> None:
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(fragment)
            except asyncio.QueueFull:
                logger.warning("fMP4 subscriber is slow; dropping its backlog")
                _discard_queued_chunks(queue)
                queue.put_nowait(self._cached_init_segment + fragment)

    async def _read_box(self) -> bytes | None:
        header = await self._read_exactly(8)
        if header is None:
            return None

        box_size = int.from_bytes(header[:4], "big")
        if box_size == 1:
            extended_size = await self._read_exactly(8)
            if extended_size is None:
                return None
            box_size = int.from_bytes(extended_size, "big")
            header += extended_size
        if box_size < len(header):
            logger.error("Invalid MP4 box size %d; aborting reader", box_size)
            return None

        rest = await self._read_exactly(box_size - len(header))
        return None if rest is None else header + rest

    async def _read_exactly(self, size: int) -> bytes | None:
        assert self._process is not None and self._process.stdout is not None
        try:
            return await self._process.stdout.readexactly(size)
        except asyncio.IncompleteReadError as error:
            logger.debug(
                "fMP4 livestream reached EOF while reading %d bytes (read %d)",
                size,
                len(error.partial),
            )
            return None

    async def stop(self) -> None:
        process = self._process
        if process is None:
            return

        await self._stop_writer()
        if process.stdin is not None:
            process.stdin.close()
        if self._reader_task is not None:
            await self._reader_task

        try:
            return_code = await asyncio.wait_for(process.wait(), timeout=5.0)
        except TimeoutError:
            logger.warning("FFmpeg process did not exit in time; killing it")
            process.kill()
            return_code = await process.wait()
        finally:
            self._process = None
            self._reader_task = None
            _discard_queued_chunks(self._frame_queue)
            self._end_subscribers()

        if return_code != 0:
            logger.warning("fMP4 livestream ffmpeg exited with code %s", return_code)

    async def _stop_writer(self) -> None:
        writer, self._writer_task = self._writer_task, None
        if writer is not None:
            writer.cancel()
            await asyncio.gather(writer, return_exceptions=True)

    def _end_subscribers(self) -> None:
        for queue in tuple(self._subscribers):
            _discard_queued_chunks(queue)
            queue.put_nowait(_STREAM_ENDED)

    def _reset_encoding_state(self) -> None:
        self._cached_init_segment = b""
        self._is_finding_init = True
        self._init_boxes.clear()
        self._fragment_boxes.clear()
        _discard_queued_chunks(self._frame_queue)


class Fmp4FrameStream:
    """Adapt complete image frames to fragmented MP4 chunks.

    Every subscription drives its own encoder, so a late consumer receives an
    init segment before the fragments that depend on it.
    """

    def __init__(self, source: FrameStream) -> None:
        self._source = source

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[AsyncIterator[bytes]]:
        livestream = Fmp4Livestream()
        publisher: asyncio.Task[None] | None = None
        try:
            await livestream.start()
            async with (
                self._source.subscribe() as frames,
                livestream.stream() as chunks,
            ):
                publisher = asyncio.create_task(
                    _publish_frames(frames, livestream),
                    name="screencast:fmp4-publisher",
                )
                yield chunks
        finally:
            if publisher is not None:
                await cancel_and_wait(publisher)
            await livestream.stop()

    async def close(self) -> None:
        """Close the wrapped frame stream."""
        await self._source.close()


async def _publish_frames(
    frames: AsyncIterator[bytes], livestream: Fmp4Livestream
) -> None:
    try:
        async for frame in frames:
            await livestream.publish_frame(frame)
    finally:
        await livestream.stop()


def _build_ffmpeg_command(keyframe_interval_seconds: int) -> list[str]:
    keyframe_interval = keyframe_interval_seconds * _NOMINAL_FPS
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-probesize",
        "32",
        "-analyzeduration",
        "0",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-use_wallclock_as_timestamps",
        "1",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libx264",
        "-profile:v",
        "baseline",
        "-preset",
        "veryfast",
        "-tune",
        "zerolatency",
        "-pix_fmt",
        "yuv420p",
        "-fps_mode",
        "vfr",
        "-g",
        str(keyframe_interval),
        "-force_key_frames",
        f"expr:gte(t,n_forced*{keyframe_interval_seconds})",
        "-x264-params",
        f"keyint={keyframe_interval}:min-keyint=1:scenecut=0",
        "-movflags",
        "frag_keyframe+empty_moov+default_base_moof",
        "-crf",
        "23",
        "-flush_packets",
        "1",
        "-f",
        "mp4",
        "pipe:1",
    ]


def _box_type(box: bytes) -> bytes:
    return box[4:8]


def _discard_queued_chunks(queue: asyncio.Queue[object]) -> None:
    while True:
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            return
