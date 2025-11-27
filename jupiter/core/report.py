"""Reporting helpers for scan outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .scanner import FileMetadata


@dataclass(slots=True)
class ScanReport:
    """Serializable report summarizing scanner findings."""

    root: Path
    files: list[FileMetadata]

    def to_dict(self) -> dict[str, object]:
        """Represent the report as a JSON-serializable dictionary."""

        return {
            "root": str(self.root),
            "files": [self._serialize_file(metadata) for metadata in self.files],
        }

    @staticmethod
    def from_files(root: Path, files: Iterable[FileMetadata]) -> "ScanReport":
        """Build a :class:`ScanReport` from an iterator of files."""

        file_list = list(files)
        return ScanReport(root=root, files=file_list)

    @staticmethod
    def _serialize_file(metadata: FileMetadata) -> dict[str, object]:
        """Serialize a single :class:`FileMetadata` instance."""

        return {
            "path": str(metadata.path),
            "size_bytes": metadata.size_bytes,
            "modified_timestamp": metadata.modified_timestamp,
        }
