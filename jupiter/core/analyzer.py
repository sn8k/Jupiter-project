"Project analysis routines built on scan results."

from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from itertools import islice
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .scanner import FileMetadata
from .cache import CacheManager
from .quality.complexity import estimate_complexity, estimate_js_complexity
from .quality.duplication import find_duplications

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PythonProjectSummary:
    """Aggregated information about Python code in a project."""

    total_files: int = 0
    total_functions: int = 0
    total_potentially_unused_functions: int = 0
    avg_functions_per_file: float = 0.0
    quality_score: Optional[float] = None


@dataclass(slots=True)
class JsTsProjectSummary:
    """Aggregated information about JS/TS code in a project."""

    total_files: int = 0
    total_functions: int = 0
    avg_functions_per_file: float = 0.0


@dataclass(slots=True)
class AnalysisSummary:
    """Simple aggregated information on a project scan."""

    file_count: int
    total_size_bytes: int
    by_extension: dict[str, int]
    average_size_bytes: float

    python_summary: Optional[PythonProjectSummary] = None
    js_ts_summary: Optional[JsTsProjectSummary] = None
    hotspots: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    refactoring: List[Dict[str, Any]] = field(default_factory=list)

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

        js_ts_summary_str = ""
        if self.js_ts_summary:
            js_summary = self.js_ts_summary
            js_ts_summary_str = (
                f"\n\nJS/TS Project Summary:\n"
                f"  - JS/TS files: {js_summary.total_files}\n"
                f"  - Total functions: {js_summary.total_functions}\n"
                f"  - Average functions per file: {js_summary.avg_functions_per_file:.2f}"
            )

        hotspots_str = ""
        if self.hotspots:
            hotspots_str = "\n\nHotspots:"
            for name, items in self.hotspots.items():
                hotspots_str += f"\n  - {name.replace('_', ' ').capitalize()}:"
                for item in items:
                    hotspots_str += f"\n    - {item['path']} ({item['details']})"
        
        quality_str = ""
        if self.quality:
            duplication_clusters = self.quality.get("duplication_clusters", [])
            quality_str = f"\n\nQuality:\n  - Duplications: {len(duplication_clusters)} clusters"
            if duplication_clusters:
                sample_occurrences = duplication_clusters[0].get("occurrences", [])
                if sample_occurrences:
                    preview_parts = []
                    for occ in sample_occurrences[:3]:
                        func = occ.get("function")
                        location = f"{Path(occ.get('path', ''))}:{occ.get('line', '?')}"
                        preview_parts.append(f"{location}" + (f" ({func})" if func else ""))
                    preview = ", ".join(preview_parts)
                    if preview:
                        extra = max(0, len(sample_occurrences) - 3)
                        suffix = f" (+{extra} more)" if extra else ""
                        quality_str += f"\n    Example: {preview}{suffix}"

        refactoring_str = ""
        if self.refactoring:
            refactoring_str = f"\n\nRefactoring Recommendations ({len(self.refactoring)}):"
            for item in self.refactoring[:5]: # Show top 5
                refactoring_str += f"\n  - [{item['severity'].upper()}] {item['path']}: {item['details']}"
            if len(self.refactoring) > 5:
                refactoring_str += f"\n  ... and {len(self.refactoring) - 5} more."

        return base_summary + python_summary_str + js_ts_summary_str + hotspots_str + quality_str + refactoring_str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the summary."""
        data = {
            "file_count": self.file_count,
            "total_size_bytes": self.total_size_bytes,
            "average_size_bytes": self.average_size_bytes,
            "by_extension": self.by_extension,
            "hotspots": self.hotspots,
            "quality": self.quality,
            "refactoring": self.refactoring,
        }
        if self.python_summary:
            # Manually convert dataclass to dict for nested serialization
            data["python_summary"] = asdict(self.python_summary)
        if self.js_ts_summary:
            data["js_ts_summary"] = asdict(self.js_ts_summary)
        return data


class ProjectAnalyzer:
    """Aggregate scanner outputs into a concise summary."""

    def __init__(self, root: Path, no_cache: bool = False, perf_mode: bool = False) -> None:
        self.root = root
        self.no_cache = no_cache
        self.perf_mode = perf_mode
        self.cache_manager = CacheManager(root)
        self.last_scan = self.cache_manager.load_last_scan()
        self.analysis_cache = {}
        
        if not self.no_cache:
            self.analysis_cache = self.cache_manager.load_analysis_cache()

        self.dynamic_calls = {}
        if self.last_scan and "dynamic" in self.last_scan and self.last_scan["dynamic"]:
             dynamic_data = self.last_scan["dynamic"]
             if isinstance(dynamic_data, dict) and "calls" in dynamic_data:
                 self.dynamic_calls = dynamic_data["calls"]
             elif isinstance(dynamic_data, dict):
                 self.dynamic_calls = dynamic_data

    def summarize(self, files: Iterable[FileMetadata], top_n: int = 5) -> AnalysisSummary:
        """Compute aggregate metrics for ``files`` collection."""
        start_time = time.time()
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
            
            # Calculate unused functions considering dynamic analysis
            py_total_unused = 0
            for m in python_files:
                unused_funcs = m.language_analysis.get("potentially_unused_functions", [])
                if not unused_funcs:
                    continue
                
                try:
                    rel_path = m.path.relative_to(self.root)
                    rel_path_str = str(rel_path)
                    rel_path_posix = rel_path.as_posix()
                except ValueError:
                    rel_path_str = str(m.path)
                    rel_path_posix = str(m.path)

                for func in unused_funcs:
                    # Check if function was called dynamically
                    # We check both OS-specific path and POSIX path just in case
                    key = f"{rel_path_str}::{func}"
                    key_posix = f"{rel_path_posix}::{func}"
                    
                    if self.dynamic_calls.get(key, 0) == 0 and self.dynamic_calls.get(key_posix, 0) == 0:
                        py_total_unused += 1

            python_summary = PythonProjectSummary(
                total_files=py_file_count,
                total_functions=py_total_functions,
                total_potentially_unused_functions=py_total_unused,
                avg_functions_per_file=py_total_functions / py_file_count if py_file_count else 0.0,
            )

        # JS/TS summary
        js_ts_files = [
            m for m in all_files if m.file_type in ("js", "ts", "jsx", "tsx") and m.language_analysis and not m.language_analysis.get("error")
        ]
        
        js_ts_summary = None
        if js_ts_files:
            js_file_count = len(js_ts_files)
            js_total_functions = sum(len(m.language_analysis.get("defined_functions", [])) for m in js_ts_files)
            
            js_ts_summary = JsTsProjectSummary(
                total_files=js_file_count,
                total_functions=js_total_functions,
                avg_functions_per_file=js_total_functions / js_file_count if js_file_count else 0.0,
            )

        # Quality Analysis
        quality_metrics = {}
        refactoring_recommendations = []
        
        # Complexity
        complexity_scores = []
        new_analysis_cache = {}
        
        # Combine files for processing
        files_to_analyze = []
        if python_files:
            files_to_analyze.extend([(f, "py") for f in python_files])
        if js_ts_files:
            files_to_analyze.extend([(f, "js") for f in js_ts_files])
            
        for m, lang in files_to_analyze:
            file_key = str(m.path)
            # Check cache
            cached_data = self.analysis_cache.get(file_key)
            
            if (
                not self.no_cache 
                and cached_data 
                and cached_data.get("mtime") == m.modified_timestamp
                and "complexity" in cached_data
            ):
                score = cached_data["complexity"]
            else:
                if m.size_bytes > 10 * 1024 * 1024: # 10 MB limit
                    score = 0
                else:
                    if lang == "py":
                        score = estimate_complexity(m.path)
                    else:
                        score = estimate_js_complexity(m.path)
            
            # Update new cache
            new_analysis_cache[file_key] = {
                "mtime": m.modified_timestamp,
                "complexity": score
            }

            complexity_scores.append({"path": str(m.path), "score": score})
            
            # Refactoring recommendation for complexity
            if score > 15:
                severity = "high" if score > 30 else "medium"
                refactoring_recommendations.append({
                    "path": str(m.path),
                    "type": "complexity",
                    "details": f"High cyclomatic complexity ({score}). Consider splitting functions.",
                    "severity": severity
                })
        
        # Save cache
        if not self.no_cache:
            self.cache_manager.save_analysis_cache(new_analysis_cache)
        
        if complexity_scores:
            complexity_scores.sort(key=lambda x: x["score"], reverse=True)
            quality_metrics["complexity_per_file"] = complexity_scores
            
            # Add complexity hotspot
            hotspots["most_complex"] = [
                {"path": item["path"], "details": f"Complexity: {item['score']}"}
                for item in complexity_scores[:top_n]
            ]

        # Duplication
        # Check top 50 largest files (Python + JS/TS)
        all_analyzable_files = []
        if python_files: all_analyzable_files.extend(python_files)
        if js_ts_files: all_analyzable_files.extend(js_ts_files)
        
        all_analyzable_files.sort(key=lambda m: m.size_bytes, reverse=True)
        
        files_to_check = [m.path for m in all_analyzable_files[:50] if m.size_bytes < 10 * 1024 * 1024]
        
        if files_to_check:
            duplications = find_duplications(files_to_check)
            quality_metrics["duplication_clusters"] = duplications

            def _format_path(path_str: str) -> str:
                """Return a stable, relative-friendly path for reporting."""
                p = Path(path_str)
                try:
                    rel = p.relative_to(self.root)
                    return rel.as_posix()
                except ValueError:
                    return p.as_posix()
            
            # Refactoring recommendation for duplication
            for cluster in duplications:
                # Deduplicate occurrences to avoid noisy reports
                unique_locations = []
                seen_locations = set()
                for occ in cluster["occurrences"]:
                    key = (occ["path"], occ["line"])
                    if key in seen_locations:
                        continue
                    seen_locations.add(key)
                    unique_locations.append({
                        "path": _format_path(occ["path"]),
                        "line": occ["line"],
                        "function": occ.get("function"),
                        "code_excerpt": occ.get("code_excerpt")
                    })

                paths = list({loc["path"] for loc in unique_locations})
                location_preview = ", ".join(
                    f"{loc['path']}:{loc['line']}" + (f" ({loc['function']})" if loc.get("function") else "")
                    for loc in islice(unique_locations, 3)
                )
                extra_locations = max(0, len(unique_locations) - 3)

                if len(paths) > 1:
                    base_details = f"Code duplicated across {len(paths)} files."
                    severity = "high"
                else:
                    base_details = f"Code duplicated {len(cluster['occurrences'])} times in this file."
                    severity = "medium"

                details_suffix = ""
                if location_preview:
                    details_suffix = f" Locations: {location_preview}"
                    if extra_locations:
                        details_suffix += f" (+{extra_locations} more occurrences)"
                details = base_details + details_suffix
                code_excerpt = None
                if unique_locations and unique_locations[0].get("code_excerpt"):
                    excerpt = unique_locations[0]["code_excerpt"]
                    if len(excerpt) > 500:
                        excerpt = excerpt[:500] + "…"
                    code_excerpt = excerpt
                
                # Add recommendation for the first file involved
                if paths:
                    refactoring_recommendations.append({
                        "path": paths[0],
                        "type": "duplication",
                        "details": details,
                        "severity": severity,
                        "locations": unique_locations,
                        "code_excerpt": code_excerpt
                    })

        if self.perf_mode:
            logger.info(f"Analysis completed in {time.time() - start_time:.4f}s")

        return AnalysisSummary(
            file_count=file_count,
            total_size_bytes=total_size,
            by_extension=dict(extension_counter),
            average_size_bytes=average_size,
            python_summary=python_summary,
            js_ts_summary=js_ts_summary,
            hotspots=hotspots,
            quality=quality_metrics,
            refactoring=refactoring_recommendations,
        )
