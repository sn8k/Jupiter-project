"""Project scanning utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(slots=True)
class FileMetadata:
    """Basic metadata describing a discovered file."""

    path: Path
    size_bytes: int
    modified_timestamp: float

    @classmethod
    def from_path(cls, path: Path) -> "FileMetadata":
        """Create :class:`FileMetadata` from a filesystem path."""

        return cls(
            path=path,
            size_bytes=path.stat().st_size,
            modified_timestamp=path.stat().st_mtime,
        )


class ProjectScanner:
    """Scan a project directory to enumerate files."""

    def __init__(self, root: Path, ignore_hidden: bool = True) -> None:
        self.root = root
        self.ignore_hidden = ignore_hidden

    def iter_files(self) -> Iterator[FileMetadata]:
        """Yield :class:`FileMetadata` objects for files under ``root``."""

        for path in self._walk_files(self.root):
            yield FileMetadata.from_path(path)

    def _walk_files(self, root: Path) -> Iterable[Path]:
        """Iterate over files respecting ignore rules."""

        for path in root.rglob("*"):
            if path.is_dir():
                continue
            if self.ignore_hidden and any(part.startswith(".") for part in path.relative_to(root).parts):
                continue
            yield path
