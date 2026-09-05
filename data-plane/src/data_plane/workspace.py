from dataclasses import dataclass
from pathlib import Path

from data_plane.settings import DataPlaneSettings


@dataclass(frozen=True, slots=True)
class Workspace:
    """Filesystem shared by browser inputs, outputs, and derived artifacts."""

    root: Path

    @classmethod
    def from_settings(cls, settings: DataPlaneSettings) -> Workspace:
        return cls(settings.workspace_path.resolve())

    @property
    def uploads(self) -> Path:
        return self.root / "uploads"

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    @property
    def recordings(self) -> Path:
        return self.root / "recordings"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    def ensure(self) -> None:
        for directory in (
            self.uploads,
            self.downloads,
            self.recordings,
            self.artifacts,
        ):
            directory.mkdir(parents=True, exist_ok=True)
