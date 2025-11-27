"""Project analysis routines built on scan results."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .scanner import FileMetadata


@dataclass(slots=True)
class AnalysisSummary:
    """Simple aggregated information on a project scan."""

    file_count: int
    total_size_bytes: int
    by_extension: dict[str, int]
    average_size_bytes: float
    largest_files: list[FileMetadata]

    def describe(self) -> str:
        """Return a human readable multi-line summary."""

        ext_fragments = [f"{ext or '<no ext>'}: {count}" for ext, count in sorted(self.by_extension.items())]
        joined_exts = ", ".join(ext_fragments)
        largest_fragments = [f"{metadata.path} ({metadata.size_bytes} B)" for metadata in self.largest_files]
        largest_line = ", ".join(largest_fragments) if largest_fragments else "-"
        return (
            f"Files: {self.file_count}\n"
            f"Total size: {self.total_size_bytes} bytes\n"
            f"Average size: {self.average_size_bytes:.2f} bytes\n"
            f"By extension: {joined_exts}\n"
            f"Largest: {largest_line}"
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the summary."""

        return {
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "average_size_bytes": self.average_size_bytes,
            "by_extension": self.by_extension,
            "largest_files": [
                {
                    "path": str(metadata.path),
                    "size_bytes": metadata.size_bytes,
                    "modified_timestamp": metadata.modified_timestamp,
                }
                for metadata in self.largest_files
            ],
        }


class ProjectAnalyzer:
    """Aggregate scanner outputs into a concise summary."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def summarize(self, files: Iterable[FileMetadata], top_n: int = 5) -> AnalysisSummary:
        """Compute aggregate metrics for ``files`` collection."""

        file_count = 0
        total_size = 0
        extension_counter: Counter[str] = Counter()
        largest_files: list[FileMetadata] = []

        for metadata in files:
            file_count += 1
            total_size += metadata.size_bytes
            extension_counter[self._extension_of(metadata.path)] += 1
            largest_files = self._update_largest(largest_files, metadata, top_n)

        average_size = float(total_size) / file_count if file_count else 0.0

        return AnalysisSummary(
            file_count=file_count,
            total_size_bytes=total_size,
            by_extension=dict(extension_counter),
            average_size_bytes=average_size,
            largest_files=largest_files,
        )

    @staticmethod
    def _extension_of(path: Path) -> str:
        """Return normalized file extension without leading dot."""

        if not path.suffix:
            return ""
        return path.suffix.lower().lstrip(".")

    def _update_largest(
        self, existing: Sequence[FileMetadata], candidate: FileMetadata, top_n: int
    ) -> list[FileMetadata]:
        """Track the ``top_n`` largest files encountered so far."""

        combined = list(existing) + [candidate]
        combined.sort(key=lambda metadata: metadata.size_bytes, reverse=True)
        return combined[:top_n]
