"""Project analysis routines built on scan results."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .scanner import FileMetadata


@dataclass(slots=True)
class AnalysisSummary:
    """Simple aggregated information on a project scan."""

    file_count: int
    total_size_bytes: int
    by_extension: dict[str, int]

    def describe(self) -> str:
        """Return a human readable multi-line summary."""

        ext_fragments = [f"{ext or '<no ext>'}: {count}" for ext, count in sorted(self.by_extension.items())]
        joined_exts = ", ".join(ext_fragments)
        return (
            f"Files: {self.file_count}\n"
            f"Total size: {self.total_size_bytes} bytes\n"
            f"By extension: {joined_exts}"
        )


class ProjectAnalyzer:
    """Aggregate scanner outputs into a concise summary."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def summarize(self, files: Iterable[FileMetadata]) -> AnalysisSummary:
        """Compute aggregate metrics for ``files`` collection."""

        file_count = 0
        total_size = 0
        extension_counter: Counter[str] = Counter()

        for metadata in files:
            file_count += 1
            total_size += metadata.size_bytes
            extension_counter[self._extension_of(metadata.path)] += 1

        return AnalysisSummary(
            file_count=file_count,
            total_size_bytes=total_size,
            by_extension=dict(extension_counter),
        )

    @staticmethod
    def _extension_of(path: Path) -> str:
        """Return normalized file extension without leading dot."""

        if not path.suffix:
            return ""
        return path.suffix.lower().lstrip(".")
