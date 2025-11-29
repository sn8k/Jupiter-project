"""Reporting helpers for scan outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .scanner import FileMetadata


@dataclass(slots=True)
class ScanReport:
    """Serializable report summarizing scanner findings."""

    root: Path
    files: list[FileMetadata]
    schema_version: str = "1.0"
    dynamic: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, object]:
        """Represent the report as a JSON-serializable dictionary.

        The schema for this dictionary is:
        {
            "report_schema_version": "1.0",
            "root": str,
            "files": [
                {
                    "path": str,
                    "size_bytes": int,
                    "modified_timestamp": float,
                    "file_type": str,
                    "language_analysis": dict | None,
                }
            ],
            "dynamic": dict | None
        }
        """

        data = {
            "report_schema_version": self.schema_version,
            "root": str(self.root),
            "files": [self._serialize_file(metadata) for metadata in self.files],
        }
        if self.dynamic:
            data["dynamic"] = self.dynamic
        return data

    @staticmethod
    def from_files(root: Path, files: Iterable[FileMetadata]) -> "ScanReport":
        """Build a :class:`ScanReport` from an iterator of files."""

        file_list = list(files)
        return ScanReport(root=root, files=file_list)

    @staticmethod
    def _serialize_file(metadata: FileMetadata) -> dict[str, object]:
        """Serialize a single :class:`FileMetadata` instance."""

        data = {
            "path": str(metadata.path),
            "size_bytes": metadata.size_bytes,
            "modified_timestamp": metadata.modified_timestamp,
            "file_type": metadata.file_type,
        }
        if metadata.language_analysis:
            data["language_analysis"] = metadata.language_analysis
        return data
