"""History and snapshot management for Jupiter."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from jupiter import __version__

logger = logging.getLogger(__name__)


def _now_ts() -> float:
    return time.time()


def _default_label(ts: float) -> str:
    return time.strftime("Scan %Y-%m-%d %H:%M:%S", time.localtime(ts))


def _extract_functions(file_entry: Dict[str, Any], key: str = "defined_functions") -> list[str]:
    lang = file_entry.get("language_analysis") or {}
    if isinstance(lang, dict):
        raw = lang.get(key)
        if isinstance(raw, list):
            return raw
    return []


@dataclass
class SnapshotMetadata:
    """Metadata describing a stored snapshot.
    
    Note: This dataclass mirrors SnapshotMetadataModel in jupiter.server.models
    to avoid circular imports. Keep both in sync when modifying fields.
    """
    id: str
    timestamp: float
    label: str
    jupiter_version: str
    backend_name: Optional[str]
    project_root: str
    project_name: str
    file_count: int
    total_size_bytes: int
    function_count: int
    unused_function_count: int


@dataclass
class FileChange:
    path: str
    change_type: str
    size_before: Optional[int]
    size_after: Optional[int]
    functions_before: Optional[list[str]]
    functions_after: Optional[list[str]]


@dataclass
class SnapshotDiff:
    snapshot_a: SnapshotMetadata
    snapshot_b: SnapshotMetadata
    files_added: list[FileChange]
    files_removed: list[FileChange]
    files_modified: list[FileChange]
    functions_added: list[Dict[str, str]]
    functions_removed: list[Dict[str, str]]
    metrics_delta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_a": asdict(self.snapshot_a),
            "snapshot_b": asdict(self.snapshot_b),
            "diff": {
                "files_added": [asdict(change) for change in self.files_added],
                "files_removed": [asdict(change) for change in self.files_removed],
                "files_modified": [asdict(change) for change in self.files_modified],
                "functions_added": self.functions_added,
                "functions_removed": self.functions_removed,
                "metrics_delta": self.metrics_delta,
            },
        }


class HistoryManager:
    """Manages scan snapshots and history for a given project root."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.snapshots_dir = project_root / ".jupiter" / "snapshots"

    def _ensure_snapshots_dir(self) -> None:
        if not self.snapshots_dir.exists():
            self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def create_snapshot(
        self,
        report: Dict[str, Any],
        label: Optional[str] = None,
        backend_name: Optional[str] = None,
    ) -> SnapshotMetadata:
        """Persist a scan report as a snapshot on disk."""

        self._ensure_snapshots_dir()
        timestamp = _now_ts()
        snapshot_id = f"scan-{int(timestamp * 1000)}"

        if hasattr(report, "to_dict"):
            report_dict: Dict[str, Any] = report.to_dict()  # type: ignore[assignment]
        else:
            report_dict = report

        metadata = self._build_metadata(
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            report=report_dict,
            label=label,
            backend_name=backend_name,
        )

        snapshot_data = {
            "metadata": asdict(metadata),
            "report": report_dict,
        }

        filename = self.snapshots_dir / f"{snapshot_id}.json"
        with open(filename, "w", encoding="utf-8") as handle:
            json.dump(snapshot_data, handle, indent=2)
        logger.info("Created snapshot %s", snapshot_id)
        return metadata

    def list_snapshots(self) -> List[SnapshotMetadata]:
        if not self.snapshots_dir.exists():
            return []

        snapshots: list[SnapshotMetadata] = []
        for path in self.snapshots_dir.glob("scan-*.json"):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                metadata = self._metadata_from_payload(payload)
                if metadata:
                    snapshots.append(metadata)
            except Exception as exc:  # pragma: no cover - unexpected read errors
                logger.warning("Failed to read snapshot %s: %s", path, exc)

        snapshots.sort(key=lambda meta: meta.timestamp, reverse=True)
        return snapshots

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        filename = self.snapshots_dir / f"{snapshot_id}.json"
        if not filename.exists():
            return None

        with open(filename, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def compare_snapshots(self, id_a: str, id_b: str) -> SnapshotDiff:
        snapshot_a = self.get_snapshot(id_a)
        snapshot_b = self.get_snapshot(id_b)

        if not snapshot_a or not snapshot_b:
            raise ValueError("One or both snapshots not found")

        metadata_a = self._metadata_from_payload(snapshot_a)
        metadata_b = self._metadata_from_payload(snapshot_b)

        if not metadata_a or not metadata_b:
            raise ValueError("Snapshot metadata missing")

        files_a = {f["path"]: f for f in snapshot_a["report"].get("files", [])}
        files_b = {f["path"]: f for f in snapshot_b["report"].get("files", [])}

        added_paths = sorted(set(files_b) - set(files_a))
        removed_paths = sorted(set(files_a) - set(files_b))
        common_paths = sorted(set(files_a) & set(files_b))

        files_added = [
            FileChange(
                path=path,
                change_type="added",
                size_before=None,
                size_after=files_b[path].get("size_bytes"),
                functions_before=None,
                functions_after=_extract_functions(files_b[path]),
            )
            for path in added_paths
        ]

        files_removed = [
            FileChange(
                path=path,
                change_type="removed",
                size_before=files_a[path].get("size_bytes"),
                size_after=None,
                functions_before=_extract_functions(files_a[path]),
                functions_after=None,
            )
            for path in removed_paths
        ]

        files_modified: list[FileChange] = []
        for path in common_paths:
            file_a = files_a[path]
            file_b = files_b[path]
            if self._has_changed(file_a, file_b):
                files_modified.append(
                    FileChange(
                        path=path,
                        change_type="modified",
                        size_before=file_a.get("size_bytes"),
                        size_after=file_b.get("size_bytes"),
                        functions_before=_extract_functions(file_a),
                        functions_after=_extract_functions(file_b),
                    )
                )

        functions_added = self._compute_function_delta(files_a, files_b, added=True)
        functions_removed = self._compute_function_delta(files_a, files_b, added=False)

        metrics_delta = {
            "file_count": metadata_b.file_count - metadata_a.file_count,
            "total_size_bytes": metadata_b.total_size_bytes - metadata_a.total_size_bytes,
            "function_count": metadata_b.function_count - metadata_a.function_count,
            "unused_function_count": metadata_b.unused_function_count - metadata_a.unused_function_count,
        }

        return SnapshotDiff(
            snapshot_a=metadata_a,
            snapshot_b=metadata_b,
            files_added=files_added,
            files_removed=files_removed,
            files_modified=files_modified,
            functions_added=functions_added,
            functions_removed=functions_removed,
            metrics_delta=metrics_delta,
        )

    def _has_changed(self, file_a: Dict[str, Any], file_b: Dict[str, Any]) -> bool:
        return (
            file_a.get("size_bytes") != file_b.get("size_bytes")
            or file_a.get("modified_timestamp") != file_b.get("modified_timestamp")
            or _extract_functions(file_a) != _extract_functions(file_b)
        )

    def _metadata_from_payload(self, payload: Dict[str, Any]) -> Optional[SnapshotMetadata]:
        raw = payload.get("metadata")
        if not raw:
            return None
        return SnapshotMetadata(
            id=raw["id"],
            timestamp=raw["timestamp"],
            label=raw["label"],
            jupiter_version=raw.get("jupiter_version", "unknown"),
            backend_name=raw.get("backend_name"),
            project_root=raw.get("project_root", str(self.project_root)),
            project_name=raw.get("project_name", Path(raw.get("project_root", self.project_root)).name),
            file_count=raw.get("file_count", 0),
            total_size_bytes=raw.get("total_size_bytes", 0),
            function_count=raw.get("function_count", 0),
            unused_function_count=raw.get("unused_function_count", 0),
        )

    def _build_metadata(
        self,
        snapshot_id: str,
        timestamp: float,
        report: Dict[str, Any],
        label: Optional[str],
        backend_name: Optional[str],
    ) -> SnapshotMetadata:
        files = report.get("files", [])
        total_size = sum(f.get("size_bytes", 0) for f in files)
        total_functions = 0
        total_unused = 0
        for file_entry in files:
            total_functions += len(_extract_functions(file_entry))
            total_unused += len(_extract_functions(file_entry, key="potentially_unused_functions"))

        project_root = report.get("root", str(self.project_root))
        return SnapshotMetadata(
            id=snapshot_id,
            timestamp=timestamp,
            label=label or _default_label(timestamp),
            jupiter_version=__version__,
            backend_name=backend_name,
            project_root=project_root,
            project_name=Path(project_root).name,
            file_count=len(files),
            total_size_bytes=total_size,
            function_count=total_functions,
            unused_function_count=total_unused,
        )

    def _compute_function_delta(
        self,
        files_a: Dict[str, Dict[str, Any]],
        files_b: Dict[str, Dict[str, Any]],
        *,
        added: bool,
    ) -> list[Dict[str, str]]:
        """Return function-level delta.

        When ``added`` is True we look for functions present in ``files_b`` but not
        in ``files_a``. Otherwise, we do the opposite.
        """

        source_files = files_b if added else files_a
        target_files = files_a if added else files_b
        direction = "added" if added else "removed"

        changes: list[Dict[str, str]] = []
        for path, file_entry in source_files.items():
            source_funcs = set(_extract_functions(file_entry))
            target_funcs = set(_extract_functions(target_files.get(path, {})))
            delta = sorted(source_funcs - target_funcs)
            for func in delta:
                changes.append({"path": path, "function": func, "change_type": direction})
        return changes
