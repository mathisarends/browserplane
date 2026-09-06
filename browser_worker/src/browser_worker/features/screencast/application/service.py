from browser_worker.features.screencast.application.ports import (
    FrameStream,
    FrameStreamFactory,
)


class ScreencastService:
    def __init__(self, stream_factory: FrameStreamFactory) -> None:
        self._stream_factory = stream_factory
        self._stream: FrameStream | None = None
        self._cdp_url: str | None = None

    def for_browser(self, cdp_url: str) -> FrameStream:
        if self._stream is None or self._cdp_url != cdp_url:
            self._stream = self._stream_factory(cdp_url)
            self._cdp_url = cdp_url
        return self._stream

    async def release(self) -> None:
        """Close and forget the stream associated with the released browser."""
        stream = self._stream
        if stream is not None:
            await stream.close()
            if self._stream is stream:
                self._stream = None
                self._cdp_url = None

    @property
    def is_idle(self) -> bool:
        return self._stream is None
