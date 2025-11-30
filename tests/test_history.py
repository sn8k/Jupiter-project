"""Tests for snapshot history management."""

from pathlib import Path

from jupiter.core.history import HistoryManager


def _file_entry(path: str, size: int, functions: list[str] | None = None, unused: list[str] | None = None, ts: int = 1) -> dict:
    entry: dict[str, object] = {
        "path": path,
        "size_bytes": size,
        "modified_timestamp": ts,
        "file_type": Path(path).suffix.lstrip("."),
    }
    lang: dict[str, object] = {}
    if functions is not None:
        lang["defined_functions"] = functions
    if unused is not None:
        lang["potentially_unused_functions"] = unused
    if lang:
        entry["language_analysis"] = lang
    return entry


def _report(root: Path, files: list[dict]) -> dict:
    return {
        "report_schema_version": "1.0",
        "root": str(root),
        "files": files,
    }


def test_create_snapshot_persists_metadata(tmp_path):
    manager = HistoryManager(tmp_path)
    report = _report(tmp_path, [
        _file_entry("foo.py", 120, functions=["alpha", "beta"], unused=["beta"]),
        _file_entry("bar.txt", 50),
    ])

    metadata = manager.create_snapshot(report, label="Initial state")

    snapshot_file = tmp_path / ".jupiter" / "snapshots" / f"{metadata.id}.json"
    assert snapshot_file.exists()

    stored = manager.list_snapshots()
    assert len(stored) == 1
    assert stored[0].file_count == 2
    assert stored[0].function_count == 2
    assert stored[0].unused_function_count == 1
    assert stored[0].label == "Initial state"


def test_compare_snapshots_returns_structured_diff(tmp_path):
    manager = HistoryManager(tmp_path)
    report_a = _report(tmp_path, [
        _file_entry("a.py", 10, functions=["foo"], unused=["foo"], ts=1),
        _file_entry("shared.py", 20, functions=["common"], ts=1),
    ])
    report_b = _report(tmp_path, [
        _file_entry("shared.py", 25, functions=["common", "extra"], ts=2),
        _file_entry("b.py", 30, functions=["bar"], ts=1),
    ])

    meta_a = manager.create_snapshot(report_a)
    meta_b = manager.create_snapshot(report_b)

    diff = manager.compare_snapshots(meta_a.id, meta_b.id)

    assert diff.metrics_delta["file_count"] == 0
    assert len(diff.files_added) == 1
    assert diff.files_added[0].path == "b.py"
    assert len(diff.files_removed) == 1
    assert diff.files_removed[0].path == "a.py"
    assert len(diff.files_modified) == 1
    assert diff.files_modified[0].path == "shared.py"
    assert any(change["function"] == "extra" for change in diff.functions_added)
    assert any(change["function"] == "foo" for change in diff.functions_removed)
