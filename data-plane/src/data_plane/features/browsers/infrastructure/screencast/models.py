from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreencastOptions:
    """How the per-page screencasts that drive tab tracking are configured."""

    quality: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class Frame:
    target_id: str
    data: bytes


@dataclass(frozen=True, slots=True)
class VisibilityChanged:
    target_id: str
    visible: bool


@dataclass(frozen=True, slots=True)
class TargetAdded:
    target_id: str


@dataclass(frozen=True, slots=True)
class TargetRemoved:
    target_id: str


@dataclass(frozen=True, slots=True)
class TargetDetached:
    target_id: str


type StreamEvent = (
    Frame | VisibilityChanged | TargetAdded | TargetRemoved | TargetDetached
)


@dataclass(frozen=True, slots=True)
class ActiveTabChanged:
    """Chromium started showing a different page target."""

    target_id: str


@dataclass(frozen=True, slots=True)
class ActiveTabFrame:
    """A screencast frame captured from the tab that is currently shown."""

    target_id: str
    data: bytes


type PageUpdate = ActiveTabChanged | ActiveTabFrame


class VisibleTarget:
    """Select frames from the page currently reported as visible by CDP."""

    def __init__(self) -> None:
        self._target_id: str | None = None
        self._hidden: set[str] = set()

    @property
    def active(self) -> str | None:
        return self._target_id

    def remove(self, target_id: str) -> None:
        self._hidden.discard(target_id)
        if self._target_id == target_id:
            self._target_id = None

    def change_visibility(self, target_id: str, *, visible: bool) -> None:
        if visible:
            self._hidden.discard(target_id)
            self._target_id = target_id
        else:
            self._hidden.add(target_id)
            if self._target_id == target_id:
                self._target_id = None

    def frame(self, event: Frame) -> bytes | None:
        if event.target_id in self._hidden:
            return None
        if self._target_id is None:
            self._target_id = event.target_id
        return event.data if self._target_id == event.target_id else None
