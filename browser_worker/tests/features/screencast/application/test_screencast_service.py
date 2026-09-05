from tests.fakes import FakeFrameStream

from browser_worker.features.screencast.application.ports import FrameStream
from browser_worker.features.screencast.application.service import ScreencastService


def test_service_reuses_only_the_stream_for_the_same_browser() -> None:
    created_for: list[str] = []

    def create_stream(cdp_url: str) -> FrameStream:
        created_for.append(cdp_url)
        return FakeFrameStream()

    service = ScreencastService(create_stream)

    first = service.for_browser("ws://browser/one")
    repeated = service.for_browser("ws://browser/one")
    second = service.for_browser("ws://browser/two")

    assert repeated is first
    assert second is not first
    assert created_for == ["ws://browser/one", "ws://browser/two"]
