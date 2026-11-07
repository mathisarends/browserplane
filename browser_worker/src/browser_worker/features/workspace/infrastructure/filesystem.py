import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

from browser_worker.features.workspace.application import Workspace


@dataclass(frozen=True, slots=True)
class FilesystemWorkspace(Workspace):
    """Filesystem shared by browser inputs, outputs, and derived artifacts."""

    root: Path

    def ensure(self) -> None:
        for directory in self.directories:
            directory.mkdir(parents=True, exist_ok=True)

    def create_recording_directory(self, recording_id: UUID) -> Path:
        """Create and return the workspace directory for one recording."""
        self.recordings.mkdir(parents=True, exist_ok=True)
        directory = self.recordings / str(recording_id)
        directory.mkdir()
        return directory

    def isolate(self) -> Path | None:
        """Move active files out of every path visible to the next session."""
        existing = tuple(path for path in self.directories if path.exists())
        if not existing:
            return None

        destination = self.garbage / str(uuid4())
        destination.mkdir(parents=True)
        for directory in existing:
            directory.replace(destination / directory.name)
        return destination

    @staticmethod
    def delete_isolated(directory: Path) -> None:
        """Delete one already-isolated workspace without blocking release."""
        shutil.rmtree(directory)

    def clear(self) -> None:
        """Remove all worker-owned files while leaving the configured root alone."""
        for directory in self.directories:
            if directory.is_symlink() or directory.is_file():
                directory.unlink(missing_ok=True)
            elif directory.exists():
                shutil.rmtree(directory)

    def is_available(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=self.root):
                pass
        except OSError:
            return False
        return True

    def is_empty(self) -> bool:
        return not any(path.exists() for path in self.directories)
