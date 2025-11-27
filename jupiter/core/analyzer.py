"Project analysis routines built on scan results."

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .scanner import FileMetadata


@dataclass(slots=True)
class PythonProjectSummary:
    """Aggregated information about Python code in a project."""

    total_files: int = 0
    total_functions: int = 0
    total_potentially_unused_functions: int = 0
    avg_functions_per_file: float = 0.0
    # Placeholder for future quality metrics
    quality_score: Optional[float] = None


@dataclass(slots=True)
class AnalysisSummary:
    """Simple aggregated information on a project scan."""

    file_count: int
    total_size_bytes: int
    by_extension: dict[str, int]
    average_size_bytes: float

    python_summary: Optional[PythonProjectSummary] = None
    hotspots: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def describe(self) -> str:
        """Return a human readable multi-line summary."""
        ext_fragments = [f"{ext or '<no ext>'}: {count}" for ext, count in sorted(self.by_extension.items())]
        joined_exts = ", ".join(ext_fragments)

        base_summary = (
            f"Files: {self.file_count}\n"
            f"Total size: {self.total_size_bytes} bytes\n"
            f"Average size: {self.average_size_bytes:.2f} bytes\n"
            f"By extension: {joined_exts}"
        )

        python_summary_str = ""
        if self.python_summary:
            py_summary = self.python_summary
            ratio = (
                (py_summary.total_potentially_unused_functions / py_summary.total_functions * 100)
                if py_summary.total_functions > 0
                else 0
            )
            python_summary_str = (
                f"\n\nPython Project Summary:\n"
                f"  - Python files: {py_summary.total_files}\n"
                f"  - Total functions: {py_summary.total_functions}\n"
                f"  - Potentially unused functions: {py_summary.total_potentially_unused_functions} ({ratio:.1f}%)\n"
                f"  - Average functions per file: {py_summary.avg_functions_per_file:.2f}"
            )

        hotspots_str = ""
        if self.hotspots:
            hotspots_str = "\n\nHotspots:"
            for name, items in self.hotspots.items():
                hotspots_str += f"\n  - {name.replace('_', ' ').capitalize()}:"
                for item in items:
                    hotspots_str += f"\n    - {item['path']} ({item['details']})"

        return base_summary + python_summary_str + hotspots_str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the summary."""
        data = {
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "average_size_bytes": self.average_size_bytes,
            "by_extension": self.by_extension,
            "hotspots": self.hotspots,
        }
        if self.python_summary:
            # Manually convert dataclass to dict for nested serialization
            data["python_summary"] = self.python_summary.__dict__
        return data


class ProjectAnalyzer:
    """Aggregate scanner outputs into a concise summary."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def summarize(self, files: Iterable[FileMetadata], top_n: int = 5) -> AnalysisSummary:
        """Compute aggregate metrics for ``files`` collection."""
        all_files = list(files)
        file_count = len(all_files)
        total_size = sum(m.size_bytes for m in all_files)
        extension_counter: Counter[str] = Counter(m.file_type for m in all_files)
        average_size = float(total_size) / file_count if file_count else 0.0

        # Hotspots
        hotspots: Dict[str, List[Dict[str, Any]]] = {}

        all_files.sort(key=lambda m: m.size_bytes, reverse=True)
        hotspots["largest_files"] = [
            {"path": str(m.path), "details": f"{m.size_bytes} bytes"} for m in all_files[:top_n]
        ]

        python_files = [
            m for m in all_files if m.file_type == "py" and m.language_analysis and not m.language_analysis.get("error")
        ]

        if python_files:
            python_files.sort(key=lambda m: len(m.language_analysis.get("defined_functions", [])), reverse=True)
            hotspots["most_functions"] = [
                {
                    "path": str(m.path),
                    "details": f"{len(m.language_analysis.get('defined_functions', []))} functions",
                }
                for m in python_files[:top_n]
            ]

        # Python summary
        python_summary = None
        if python_files:
            py_file_count = len(python_files)
            py_total_functions = sum(len(m.language_analysis.get("defined_functions", [])) for m in python_files)
            py_total_unused = sum(
                len(m.language_analysis.get("potentially_unused_functions", [])) for m in python_files
            )
            python_summary = PythonProjectSummary(
                total_files=py_file_count,
                total_functions=py_total_functions,
                total_potentially_unused_functions=py_total_unused,
                avg_functions_per_file=py_total_functions / py_file_count if py_file_count else 0.0,
            )

        return AnalysisSummary(
            file_count=file_count,
            total_size_bytes=total_size,
            by_extension=dict(extension_counter),
            average_size_bytes=average_size,
            python_summary=python_summary,
            hotspots=hotspots,
        )