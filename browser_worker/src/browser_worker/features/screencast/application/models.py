from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScreencastOptions:
    quality: int
    width: int
    height: int
