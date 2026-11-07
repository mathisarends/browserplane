from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID


class Workspace(ABC):
    """Paths and lifecycle operations owned by the worker workspace."""

    root: Path

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

    @property
    def directories(self) -> tuple[Path, ...]:
        """Directories exclusively owned by this worker."""
        return self.uploads, self.downloads, self.recordings, self.artifacts

    @property
    def garbage(self) -> Path:
        return self.root / "garbage"

    @abstractmethod
    def ensure(self) -> None: ...

    @abstractmethod
    def create_recording_directory(self, recording_id: UUID) -> Path: ...

    @abstractmethod
    def isolate(self) -> Path | None: ...

    @staticmethod
    @abstractmethod
    def delete_isolated(directory: Path) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def is_empty(self) -> bool: ...
