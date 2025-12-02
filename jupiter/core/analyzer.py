"""
Project analysis routines built on scan results.

Version: 1.1.0
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from enum import Enum
from itertools import islice
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

from .scanner import FileMetadata
from .cache import CacheManager
from .quality.complexity import estimate_complexity, estimate_js_complexity
from .quality.duplication import find_duplications

logger = logging.getLogger(__name__)


# =============================================================================
# FUNCTION USAGE STATUS AND CONFIDENCE SCORING
# =============================================================================

class FunctionUsageStatus(str, Enum):
    """Status of function usage detection."""
    USED = "used"  # Directly called or referenced
    LIKELY_USED = "likely_used"  # Framework decorator, known pattern, or dynamically registered
    POSSIBLY_UNUSED = "possibly_unused"  # Low confidence unused (might be false positive)
    UNUSED = "unused"  # High confidence unused


@dataclass(slots=True)
class FunctionUsageInfo:
    """
    Detailed information about a function's usage status with confidence score.
    
    Attributes:
        name: Function name
        file_path: Path to the file containing the function
        status: Usage status (used, likely_used, possibly_unused, unused)
        confidence: Confidence score (0.0 = no confidence, 1.0 = high confidence)
        reasons: List of reasons explaining the status
    """
    name: str
    file_path: str
    status: FunctionUsageStatus
    confidence: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "name": self.name,
            "file_path": self.file_path,
            "status": self.status.value,
            "confidence": round(self.confidence, 2),
            "reasons": self.reasons,
        }


def compute_function_confidence(
    func_name: str,
    is_called: bool,
    is_decorated: bool,
    is_dynamically_registered: bool,
    is_known_pattern: bool,
    has_docstring: bool = False,
    is_public: bool = True,
) -> tuple[FunctionUsageStatus, float, List[str]]:
    """
    Compute usage status and confidence score for a function.
    
    Scoring logic:
    - Directly called: USED, confidence 1.0
    - Framework decorator: LIKELY_USED, confidence 0.95
    - Dynamically registered: LIKELY_USED, confidence 0.90
    - Known pattern (dunder, serialization): LIKELY_USED, confidence 0.85
    - Private function (_prefix): POSSIBLY_UNUSED, confidence 0.60
    - Public function, no calls: UNUSED, confidence 0.75
    - Public function with docstring: POSSIBLY_UNUSED, confidence 0.50
    
    Returns:
        Tuple of (status, confidence, reasons)
    """
    reasons: List[str] = []
    
    # Direct call - highest confidence
    if is_called:
        reasons.append("directly_called")
        return FunctionUsageStatus.USED, 1.0, reasons
    
    # Framework decorator - very high confidence
    if is_decorated:
        reasons.append("has_framework_decorator")
        return FunctionUsageStatus.LIKELY_USED, 0.95, reasons
    
    # Dynamic registration - high confidence
    if is_dynamically_registered:
        reasons.append("dynamically_registered")
        return FunctionUsageStatus.LIKELY_USED, 0.90, reasons
    
    # Known patterns (dunder, hooks, etc.)
    if is_known_pattern:
        reasons.append("matches_known_pattern")
        return FunctionUsageStatus.LIKELY_USED, 0.85, reasons
    
    # Private function (starts with _)
    if func_name.startswith("_") and not func_name.startswith("__"):
        reasons.append("private_function")
        if has_docstring:
            reasons.append("has_docstring")
            return FunctionUsageStatus.POSSIBLY_UNUSED, 0.55, reasons
        return FunctionUsageStatus.POSSIBLY_UNUSED, 0.65, reasons
    
    # Public function without any usage signals
    if is_public:
        if has_docstring:
            reasons.append("public_with_docstring")
            return FunctionUsageStatus.POSSIBLY_UNUSED, 0.50, reasons
        reasons.append("no_usage_found")
        return FunctionUsageStatus.UNUSED, 0.75, reasons
    
    reasons.append("no_usage_found")
    return FunctionUsageStatus.UNUSED, 0.70, reasons


@dataclass(slots=True)
class PythonProjectSummary:
    """Aggregated information about Python code in a project."""

    total_files: int = 0
    total_functions: int = 0
    total_potentially_unused_functions: int = 0
    avg_functions_per_file: float = 0.0
    quality_score: Optional[float] = None
    # Phase 2: Detailed function usage with confidence scores
    function_usage_details: List[Dict[str, Any]] = field(default_factory=list)
    usage_summary: Dict[str, int] = field(default_factory=dict)  # Count per status


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

    def __init__(
        self, 
        root: Path, 
        no_cache: bool = False, 
        perf_mode: bool = False,
        use_callgraph: bool = True,  # Use global call graph for unused detection
    ) -> None:
        self.root = root
        self.no_cache = no_cache
        self.perf_mode = perf_mode
        self.use_callgraph = use_callgraph
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

    def _build_callgraph_unused_set(self, python_files: List[FileMetadata]) -> set[str]:
        """
        Build a set of unused function keys using the global call graph.
        
        Returns set of "file_path::func_name" keys that are unused.
        """
        from .callgraph import build_call_graph
        
        # Get file paths
        file_paths = [m.path for m in python_files]
        
        # Build call graph
        result = build_call_graph(self.root, file_paths)
        
        # Return the unused set using simple_key format (file::func without class)
        return {
            result.all_functions[key].simple_key 
            for key in result.unused_functions
        }

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
            python_files.sort(key=lambda m: len((m.language_analysis or {}).get("defined_functions", [])), reverse=True)
            hotspots["most_functions"] = [
                {
                    "path": str(m.path),
                    "details": f"{len((m.language_analysis or {}).get('defined_functions', []))} functions",
                }
                for m in python_files[:top_n]
            ]

        # Python summary with call graph analysis
        python_summary = None
        if python_files:
            py_file_count = len(python_files)
            py_total_functions = sum(len((m.language_analysis or {}).get("defined_functions", [])) for m in python_files)
            
            # Calculate unused functions
            py_total_unused = 0
            function_usage_details: List[Dict[str, Any]] = []
            usage_counts: Dict[str, int] = {
                FunctionUsageStatus.USED.value: 0,
                FunctionUsageStatus.LIKELY_USED.value: 0,
                FunctionUsageStatus.POSSIBLY_UNUSED.value: 0,
                FunctionUsageStatus.UNUSED.value: 0,
            }
            
            # Build call graph for accurate unused detection
            callgraph_unused: set[str] = set()
            if self.use_callgraph:
                try:
                    callgraph_unused = self._build_callgraph_unused_set(python_files)
                    logger.debug(f"Call graph detected {len(callgraph_unused)} unused functions")
                except Exception as e:
                    logger.warning(f"Call graph analysis failed, falling back to per-file: {e}")
                    self.use_callgraph = False
            
            for m in python_files:
                la = m.language_analysis or {}
                defined_funcs = la.get("defined_functions", [])
                function_calls = set(la.get("function_calls", []))
                decorated_funcs = set(la.get("decorated_functions", []))
                dynamically_registered = set(la.get("dynamically_registered", []))
                
                try:
                    rel_path = m.path.relative_to(self.root)
                    rel_path_str = rel_path.as_posix()
                except ValueError:
                    rel_path_str = str(m.path)
                
                for func in defined_funcs:
                    key = f"{rel_path_str}::{func}"
                    
                    # Check dynamic calls from runtime analysis
                    dynamically_called = self.dynamic_calls.get(key, 0) > 0
                    
                    # Use call graph for unused detection
                    if self.use_callgraph:
                        # Call graph gives us definitive unused status
                        if key in callgraph_unused and not dynamically_called:
                            status = FunctionUsageStatus.UNUSED
                            confidence = 0.95  # High confidence from call graph
                            reasons = ["not_referenced_in_callgraph"]
                        else:
                            status = FunctionUsageStatus.USED
                            confidence = 1.0
                            reasons = ["referenced_in_callgraph"]
                            if dynamically_called:
                                reasons.append("called_at_runtime")
                    else:
                        # Fallback to old per-file analysis
                        from .language.python import is_likely_used
                        status, confidence, reasons = compute_function_confidence(
                            func_name=func,
                            is_called=func in function_calls or dynamically_called,
                            is_decorated=func in decorated_funcs,
                            is_dynamically_registered=func in dynamically_registered,
                            is_known_pattern=is_likely_used(func),
                            has_docstring=False,
                            is_public=not func.startswith("_"),
                        )
                    
                    usage_counts[status.value] += 1
                    
                    # Only include non-USED functions in details
                    if status != FunctionUsageStatus.USED:
                        usage_info = FunctionUsageInfo(
                            name=func,
                            file_path=rel_path_str,
                            status=status,
                            confidence=confidence,
                            reasons=reasons,
                        )
                        function_usage_details.append(usage_info.to_dict())
                        
                        if status == FunctionUsageStatus.UNUSED:
                            py_total_unused += 1

            # Sort by confidence descending
            function_usage_details.sort(key=lambda x: (-x["confidence"], x["status"], x["name"]))

            python_summary = PythonProjectSummary(
                total_files=py_file_count,
                total_functions=py_total_functions,
                total_potentially_unused_functions=py_total_unused,
                avg_functions_per_file=py_total_functions / py_file_count if py_file_count else 0.0,
                function_usage_details=function_usage_details,
                usage_summary=usage_counts,
            )

        # JS/TS summary
        js_ts_files = [
            m for m in all_files if m.file_type in ("js", "ts", "jsx", "tsx") and m.language_analysis and not m.language_analysis.get("error")
        ]
        
        js_ts_summary = None
        if js_ts_files:
            js_file_count = len(js_ts_files)
            js_total_functions = sum(len((m.language_analysis or {}).get("defined_functions", [])) for m in js_ts_files)
            
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
                occurrences = cast(List[Dict[str, Any]], cluster.get("occurrences", []))
                for occ in occurrences:
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
                    base_details = f"Code duplicated {len(occurrences)} times in this file."
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
