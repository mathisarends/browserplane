from data_plane.features.browsers.infrastructure.screencast.models import (
    Frame,
    VisibleTarget,
)


def test_screencast_frames_follow_the_visible_target() -> None:
    target = VisibleTarget()

    target.change_visibility("first", visible=True)
    assert target.frame(Frame("first", b"first")) == b"first"

    target.change_visibility("first", visible=False)
    target.change_visibility("second", visible=True)

    assert target.frame(Frame("first", b"stale")) is None
    assert target.frame(Frame("second", b"second")) == b"second"
