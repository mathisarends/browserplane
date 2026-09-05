from data_plane.features.screencast.application.ports import (
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
