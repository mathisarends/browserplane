from data_plane.features.browsers.infrastructure.screencast import (
    _Frame,
    _VisibleTarget,
)


def test_screencast_frames_follow_the_visible_target() -> None:
    target = _VisibleTarget()

    target.change_visibility("first", visible=True)
    assert target.frame(_Frame("first", b"first")) == b"first"

    target.change_visibility("first", visible=False)
    target.change_visibility("second", visible=True)

    assert target.frame(_Frame("first", b"stale")) is None
    assert target.frame(_Frame("second", b"second")) == b"second"
