"""Project scanning utilities."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
from pathlib import Path
from typing import Iterable, Iterator, Optional, Dict, Any

from jupiter.core.language.python import analyze_python_source


@dataclass(slots=True)
class FileMetadata:
    """Basic metadata describing a discovered file."""

    path: Path
    size_bytes: int
    modified_timestamp: float
    file_type: str
    language_analysis: Optional[Dict[str, Any]] = None

    @classmethod
    def from_path(cls, path: Path) -> "FileMetadata":
        """Create :class:`FileMetadata` from a filesystem path."""

        return cls(
            path=path,
            size_bytes=path.stat().st_size,
            modified_timestamp=path.stat().st_mtime,
            file_type=path.suffix.lower().lstrip("."),
        )


class ProjectScanner:
    """Scan a project directory to enumerate files."""

    def __init__(
        self,
        root: Path,
        ignore_hidden: bool = True,
        ignore_globs: list[str] | None = None,
        ignore_file: str = ".jupiterignore",
    ) -> None:
        self.root = root
        self.ignore_hidden = ignore_hidden
        self.ignore_patterns = self._resolve_ignore_patterns(ignore_globs, ignore_file)

    def iter_files(self) -> Iterator[FileMetadata]:
        """Yield :class:`FileMetadata` objects for files under ``root``."""

        for path in self._walk_files(self.root):
            metadata = FileMetadata.from_path(path)
            if metadata.file_type == "py":
                try:
                    source = path.read_text(encoding="utf-8")
                    metadata.language_analysis = analyze_python_source(source)
                except Exception as e:
                    metadata.language_analysis = {"error": f"Could not read or parse file: {e}"}
            yield metadata

    def _walk_files(self, root: Path) -> Iterable[Path]:
        """Iterate over files respecting ignore rules."""

        for path in root.rglob("*"):
            if path.is_dir():
                continue
            relative_path = path.relative_to(root)
            if self.ignore_hidden and any(part.startswith(".") for part in relative_path.parts):
                continue
            if self._should_ignore(relative_path):
                continue
            yield path

    def _should_ignore(self, relative_path: Path) -> bool:
        """Return whether a path should be skipped based on ignore patterns."""

        relative_str = relative_path.as_posix()
        return any(fnmatch.fnmatch(relative_str, pattern) for pattern in self.ignore_patterns)

    def _resolve_ignore_patterns(self, patterns: list[str] | None, ignore_file: str) -> list[str]:
        """Load ignore patterns from an ignore file and explicit arguments.

        If an ignore file exists at the project root, its patterns are loaded.
        Any patterns passed via the ``patterns`` argument are then appended to
        this list.
        """

        all_patterns: list[str] = []
        ignore_path = self.root / ignore_file
        if ignore_path.exists():
            for line in ignore_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                all_patterns.append(stripped)

        if patterns is not None:
            all_patterns.extend(patterns)

        return all_patterns
