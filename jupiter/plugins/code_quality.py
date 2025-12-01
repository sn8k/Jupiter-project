"""Code Quality plugin for Jupiter.

This plugin provides comprehensive code quality analysis including:
- Cyclomatic complexity analysis per file and function
- Code duplication detection
- Maintainability index calculation
- Overall quality score computation
- Detailed issues and recommendations

The plugin integrates with Jupiter's existing quality analysis tools
in jupiter/core/quality/ and enriches scan/analyze reports.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from jupiter.plugins import PluginUIConfig, PluginUIType
from jupiter.core.quality.complexity import estimate_complexity, estimate_js_complexity
from jupiter.core.quality.duplication import find_duplications

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "0.8.1"


# === Thresholds ===
COMPLEXITY_THRESHOLDS = {
    "low": 10,       # 1-10: simple, low risk
    "moderate": 20,  # 11-20: moderate complexity
    "high": 30,      # 21-30: high complexity, consider refactoring
    "very_high": 50  # 31+: very high, should be split
}

DUPLICATION_THRESHOLDS = {
    "acceptable": 3,  # Up to 3% duplication is acceptable
    "warning": 5,     # 3-5% is a warning
    "high": 10        # 5-10% is high
}


@dataclass
class QualityIssue:
    """A single quality issue found during analysis."""
    
    file: str
    line: Optional[int]
    severity: str  # "info", "warning", "error"
    category: str  # "complexity", "duplication", "maintainability"
    message: str
    suggestion: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FileQualityReport:
    """Quality metrics for a single file."""
    
    path: str
    complexity: int = 0
    complexity_grade: str = "A"  # A, B, C, D, F
    lines_of_code: int = 0
    comment_ratio: float = 0.0
    maintainability_index: float = 100.0
    issues: List[QualityIssue] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "complexity": self.complexity,
            "complexity_grade": self.complexity_grade,
            "lines_of_code": self.lines_of_code,
            "comment_ratio": self.comment_ratio,
            "maintainability_index": round(self.maintainability_index, 2),
            "issues": [i.to_dict() for i in self.issues],
        }


@dataclass
class QualitySummary:
    """Summary of code quality across all analyzed files."""
    
    total_files: int = 0
    total_lines: int = 0
    average_complexity: float = 0.0
    average_maintainability: float = 100.0
    duplication_percentage: float = 0.0
    overall_score: float = 100.0
    overall_grade: str = "A"
    total_issues: int = 0
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_category: Dict[str, int] = field(default_factory=dict)
    file_reports: List[FileQualityReport] = field(default_factory=list)
    duplication_clusters: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "average_complexity": round(self.average_complexity, 2),
            "average_maintainability": round(self.average_maintainability, 2),
            "duplication_percentage": round(self.duplication_percentage, 2),
            "overall_score": round(self.overall_score, 2),
            "overall_grade": self.overall_grade,
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues_by_category": self.issues_by_category,
            "file_reports": [f.to_dict() for f in self.file_reports],
            "duplication_clusters": self.duplication_clusters,
            "recommendations": self.recommendations,
        }


@dataclass
class ManualLinkOccurrence:
    """Single occurrence entry for a manually linked duplication block."""

    path: str
    start_line: int
    end_line: int
    label: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManualLinkOccurrence":
        try:
            path = data["path"]
            raw_start = data.get("start_line")
            if raw_start is None:
                raw_start = data.get("line")
            if raw_start is None:
                raise ValueError("Missing start_line")
            start = int(raw_start)
            raw_end = data.get("end_line")
            end = int(raw_end) if raw_end is not None else start
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid manual link occurrence: {data}") from exc
        if end < start:
            end = start
        return cls(path=str(path), start_line=start, end_line=end, label=data.get("label"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "label": self.label,
        }


@dataclass
class ManualDuplicationLink:
    """Represents a user-defined linkage between duplication clusters."""

    link_id: str
    label: Optional[str]
    occurrences: List[ManualLinkOccurrence] = field(default_factory=list)
    origin: str = "config"  # config or file

    @classmethod
    def from_dict(cls, data: dict[str, Any], origin: str = "config") -> "ManualDuplicationLink":
        if "id" in data:
            link_id = str(data["id"])
        elif "link_id" in data:
            link_id = str(data["link_id"])
        else:
            raise ValueError("Manual link missing 'id'")
        occurrences_data = data.get("occurrences", [])
        if len(occurrences_data) < 2:
            raise ValueError(f"Manual link '{link_id}' must have at least two occurrences")
        occurrences = [ManualLinkOccurrence.from_dict(item) for item in occurrences_data]
        return cls(link_id=link_id, label=data.get("label"), occurrences=occurrences, origin=origin)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.link_id,
            "label": self.label,
            "occurrences": [occ.to_dict() for occ in self.occurrences],
            "origin": self.origin,
        }


class CodeQualityPlugin:
    """Comprehensive code quality analysis plugin.
    
    This plugin provides real code quality metrics including:
    - Cyclomatic complexity per file
    - Code duplication detection
    - Maintainability index calculation
    - Overall quality scoring
    
    Configuration options:
        enabled: bool - Whether to run analysis (default: True)
        max_files: int - Maximum files to analyze (default: 200)
        complexity_threshold: int - Threshold for complexity warnings (default: 15)
        duplication_chunk_size: int - Lines per chunk for duplication detection (default: 6)
        include_tests: bool - Include test files in analysis (default: False)
    """

    name = "code_quality"
    version = PLUGIN_VERSION
    description = "Comprehensive code quality analysis with complexity, duplication, and maintainability metrics."
    trust_level = "stable"
    
    # UI Configuration - shows in sidebar
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.BOTH,
        menu_icon="📊",
        menu_label_key="code_quality_view",
        menu_order=65,  # Before Pylance (75)
        view_id="code_quality",
        settings_section="Code Quality",
    )

    def __init__(self) -> None:
        self.enabled = True
        self.max_files = 200
        self.complexity_threshold = 15
        self.duplication_chunk_size = 6
        self.include_tests = False
        self._last_summary: Optional[QualitySummary] = None
        self._project_root: Optional[Path] = None
        self.config: Dict[str, Any] = {}
        self.manual_links: Dict[str, ManualDuplicationLink] = {}
        self._manual_links_file: Optional[Path] = None
        self._manual_file_cache: Dict[str, List[str]] = {}

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the plugin with the given settings."""
        self.config = config
        self.enabled = config.get("enabled", True)
        self.max_files = config.get("max_files", 200)
        self.complexity_threshold = config.get("complexity_threshold", 15)
        self.duplication_chunk_size = config.get("duplication_chunk_size", 6)
        self.include_tests = config.get("include_tests", False)
        self._reload_manual_links()
        logger.info(
            "CodeQualityPlugin configured: enabled=%s, max_files=%d, threshold=%d",
            self.enabled, self.max_files, self.complexity_threshold
        )
        logger.debug(
            "CodeQualityPlugin config include_tests=%s chunk_size=%d manual_links=%d",
            self.include_tests,
            self.duplication_chunk_size,
            len(self.manual_links),
        )

    def _get_complexity_grade(self, complexity: int) -> str:
        """Convert complexity score to letter grade."""
        if complexity <= COMPLEXITY_THRESHOLDS["low"]:
            return "A"
        elif complexity <= COMPLEXITY_THRESHOLDS["moderate"]:
            return "B"
        elif complexity <= COMPLEXITY_THRESHOLDS["high"]:
            return "C"
        elif complexity <= COMPLEXITY_THRESHOLDS["very_high"]:
            return "D"
        else:
            return "F"

    def _get_overall_grade(self, score: float) -> str:
        """Convert overall score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _count_lines_and_comments(self, file_path: Path) -> tuple[int, int]:
        """Count total lines and comment lines in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, OSError):
            return 0, 0
        
        total = len(lines)
        comments = 0
        is_python = file_path.suffix == ".py"
        in_multiline = False
        
        for line in lines:
            stripped = line.strip()
            if is_python:
                # Python comments
                if in_multiline:
                    comments += 1
                    if '"""' in stripped or "'''" in stripped:
                        in_multiline = False
                elif stripped.startswith("#"):
                    comments += 1
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    comments += 1
                    if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                        in_multiline = True
            else:
                # JS/TS style comments
                if in_multiline:
                    comments += 1
                    if "*/" in stripped:
                        in_multiline = False
                elif stripped.startswith("//"):
                    comments += 1
                elif stripped.startswith("/*"):
                    comments += 1
                    if "*/" not in stripped:
                        in_multiline = True
        
        return total, comments

    def _calculate_maintainability_index(
        self, 
        lines_of_code: int, 
        complexity: int, 
        comment_ratio: float
    ) -> float:
        """Calculate maintainability index (0-100).
        
        Based on the formula:
        MI = 171 - 5.2 * ln(Halstead Volume) - 0.23 * (Cyclomatic Complexity) - 16.2 * ln(LOC)
        
        Since we don't compute Halstead Volume, we use a simplified approximation.
        """
        if lines_of_code == 0:
            return 100.0
        
        # Simplified maintainability index
        # Base: 100
        # Penalty for complexity: -0.5 per point above threshold
        # Penalty for size: logarithmic penalty for large files
        # Bonus for comments: up to +5 for good documentation
        
        base = 100.0
        
        # Complexity penalty
        if complexity > self.complexity_threshold:
            base -= (complexity - self.complexity_threshold) * 0.5
        
        # Size penalty (logarithmic for files > 200 lines)
        if lines_of_code > 200:
            base -= min(20, 5 * math.log10(lines_of_code / 200))
        
        # Comment bonus (up to +5 for 20%+ comment ratio)
        if comment_ratio > 0.05:
            base += min(5, comment_ratio * 25)
        
        return max(0, min(100, base))

    def _analyze_file(self, file_path: Path) -> FileQualityReport:
        """Analyze a single file for quality metrics."""
        path_str = str(file_path)
        report = FileQualityReport(path=path_str)
        
        # Determine language
        suffix = file_path.suffix.lower()
        is_python = suffix == ".py"
        is_js_ts = suffix in (".js", ".ts", ".jsx", ".tsx")
        
        if not (is_python or is_js_ts):
            return report
        
        # Count lines
        total_lines, comment_lines = self._count_lines_and_comments(file_path)
        report.lines_of_code = total_lines
        report.comment_ratio = comment_lines / total_lines if total_lines > 0 else 0.0
        
        # Calculate complexity
        if is_python:
            report.complexity = estimate_complexity(file_path)
        else:
            report.complexity = estimate_js_complexity(file_path)
        
        report.complexity_grade = self._get_complexity_grade(report.complexity)
        
        # Calculate maintainability
        report.maintainability_index = self._calculate_maintainability_index(
            report.lines_of_code,
            report.complexity,
            report.comment_ratio
        )
        
        # Generate issues
        if report.complexity > COMPLEXITY_THRESHOLDS["very_high"]:
            report.issues.append(QualityIssue(
                file=path_str,
                line=None,
                severity="error",
                category="complexity",
                message=f"Very high complexity ({report.complexity}). This file is difficult to maintain.",
                suggestion="Split into smaller functions or modules."
            ))
        elif report.complexity > COMPLEXITY_THRESHOLDS["high"]:
            report.issues.append(QualityIssue(
                file=path_str,
                line=None,
                severity="warning",
                category="complexity",
                message=f"High complexity ({report.complexity}). Consider refactoring.",
                suggestion="Extract complex logic into separate functions."
            ))
        
        if report.lines_of_code > 500:
            report.issues.append(QualityIssue(
                file=path_str,
                line=None,
                severity="warning",
                category="maintainability",
                message=f"Large file ({report.lines_of_code} lines).",
                suggestion="Consider splitting into multiple modules."
            ))
        
        if report.comment_ratio < 0.05 and report.lines_of_code > 100:
            report.issues.append(QualityIssue(
                file=path_str,
                line=None,
                severity="info",
                category="maintainability",
                message="Low comment ratio. Consider adding documentation.",
                suggestion="Add docstrings and inline comments for complex logic."
            ))
        
        return report

    def _filter_files(self, files: List[Dict[str, Any]]) -> List[Path]:
        """Filter files for analysis based on configuration."""
        result = []
        considered = 0
        skipped_non_code = 0
        skipped_tests = 0
        
        for file_info in files:
            path_str = file_info.get("path", "")
            if not path_str:
                continue
            considered += 1
            
            path = Path(path_str)
            suffix = path.suffix.lower()
            
            # Only analyze Python and JS/TS files
            if suffix not in (".py", ".js", ".ts", ".jsx", ".tsx"):
                skipped_non_code += 1
                continue
            
            # Skip test files if configured
            if not self.include_tests:
                name_lower = path.name.lower()
                path_lower = str(path).lower()
                if any(pattern in name_lower or pattern in path_lower for pattern in 
                       ["test_", "_test", "tests/", "test/", ".test.", ".spec."]):
                    skipped_tests += 1
                    continue
            
            result.append(path)

        limited = result[:self.max_files]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "CodeQualityPlugin filtered files: considered=%d kept=%d skipped_non_code=%d skipped_tests=%d limit=%d",
                considered,
                len(limited),
                skipped_non_code,
                skipped_tests,
                self.max_files,
            )

        return limited

    def on_scan(self, report: dict[str, Any]) -> None:
        """Add quality metrics to the scan report."""
        if not self.enabled:
            logger.debug("CodeQualityPlugin disabled; skipping on_scan")
            return
        
        logger.info("CodeQualityPlugin: analyzing scan report...")
        
        files = report.get("files", [])
        if not files:
            report["code_quality"] = {
                "status": "no_files",
                "message": "No files to analyze."
            }
            logger.warning("CodeQualityPlugin: scan report had no files")
            return
        
        # Get project root
        project_path = report.get("project_path")
        if project_path:
            self._project_root = Path(project_path)
            self._reload_manual_links()
        
        # Filter files for analysis
        files_to_analyze = self._filter_files(files)
        
        if not files_to_analyze:
            report["code_quality"] = {
                "status": "no_analyzable_files",
                "message": "No Python or JS/TS files found for analysis."
            }
            logger.info("CodeQualityPlugin: no eligible files after filtering")
            return
        
        # Quick summary for scan (full analysis in on_analyze)
        sample_size = min(10, len(files_to_analyze))
        sample_files = files_to_analyze[:sample_size]
        
        sample_complexities = []
        for fp in sample_files:
            if fp.suffix == ".py":
                sample_complexities.append(estimate_complexity(fp))
            else:
                sample_complexities.append(estimate_js_complexity(fp))
        
        avg_complexity = sum(sample_complexities) / len(sample_complexities) if sample_complexities else 0
        
        report["code_quality"] = {
            "status": "ok",
            "files_analyzed": len(files_to_analyze),
            "sample_avg_complexity": round(avg_complexity, 2),
            "complexity_grade": self._get_complexity_grade(int(avg_complexity)),
            "message": f"Analyzed {len(files_to_analyze)} files. Average complexity: {avg_complexity:.1f}"
        }
        
        logger.info("CodeQualityPlugin: scan analysis complete. %d files, avg complexity: %.1f",
                    len(files_to_analyze), avg_complexity)
        if logger.isEnabledFor(logging.DEBUG):
            sample_paths = [str(path) for path in sample_files]
            logger.debug(
                "CodeQualityPlugin scan sample paths=%s grade=%s",
                sample_paths,
                report["code_quality"]["complexity_grade"],
            )

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """Add comprehensive quality metrics to the analysis summary."""
        if not self.enabled:
            logger.debug("CodeQualityPlugin disabled; skipping on_analyze")
            return
        
        logger.info("CodeQualityPlugin: performing full quality analysis...")
        
        # Try to get project root from various sources
        if not self._project_root:
            # Try from hotspots paths
            hotspots = summary.get("hotspots", {})
            if isinstance(hotspots, dict):
                for category_items in hotspots.values():
                    if isinstance(category_items, list) and category_items:
                        first_item = category_items[0]
                        path_str = first_item.path if hasattr(first_item, "path") else first_item.get("path", "") if isinstance(first_item, dict) else ""
                        if path_str:
                            # Try to find a reasonable project root
                            path = Path(path_str)
                            if path.exists():
                                # Go up to find a directory that looks like a project root
                                for parent in path.parents:
                                    if (parent / ".git").exists() or (parent / "pyproject.toml").exists() or (parent / "package.json").exists():
                                        self._project_root = parent
                                        break
                                if not self._project_root:
                                    self._project_root = path.parent
                                break
        
        logger.info("CodeQualityPlugin: project root = %s", self._project_root)
        self._reload_manual_links()
        
        # Build list of files to analyze
        # We need to find files from the available data sources
        files_to_analyze: List[Path] = []
        
        # Method 1: Try to get files from hotspots (this works even after Pydantic conversion)
        hotspots = summary.get("hotspots", {})
        if isinstance(hotspots, dict):
            for category_items in hotspots.values():
                if isinstance(category_items, list):
                    for item in category_items:
                        # Handle both dict and Pydantic model
                        if hasattr(item, "path"):
                            path_str = item.path
                        elif isinstance(item, dict):
                            path_str = item.get("path", "")
                        else:
                            continue
                        
                        if path_str:
                            path = Path(path_str)
                            if path.exists() and path.suffix in (".py", ".js", ".ts", ".jsx", ".tsx"):
                                if path not in files_to_analyze:
                                    files_to_analyze.append(path)
        
        # Method 2: Try to load from last scan cache if we have a project root
        if not files_to_analyze and self._project_root:
            try:
                from jupiter.core.cache import CacheManager
                cache_manager = CacheManager(self._project_root)
                last_scan = cache_manager.load_last_scan()
                if last_scan and "files" in last_scan:
                    files_to_analyze = self._filter_files(last_scan["files"])
            except Exception as e:
                logger.warning("Could not load files from cache: %s", e)
        
        # Method 3: Scan the project root directory
        if not files_to_analyze and self._project_root and self._project_root.exists():
            logger.info("Scanning project root for files: %s", self._project_root)
            for pattern in ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"]:
                for path in self._project_root.glob(pattern):
                    if path.is_file():
                        # Skip common excluded directories
                        path_str = str(path).lower()
                        if any(skip in path_str for skip in ["node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build"]):
                            continue
                        if not self.include_tests:
                            if any(t in path.name.lower() or t in path_str for t in ["test_", "_test", "tests/", ".test.", ".spec."]):
                                continue
                        if path not in files_to_analyze:
                            files_to_analyze.append(path)
        
        files_to_analyze = files_to_analyze[:self.max_files]
        
        if not files_to_analyze:
            summary["code_quality"] = {
                "status": "no_files",
                "overall_score": 100,
                "overall_grade": "A",
                "total_files": 0,
                "total_lines": 0,
                "average_complexity": 0,
                "average_maintainability": 100,
                "duplication_percentage": 0,
                "total_issues": 0,
                "issues_by_severity": {},
                "issues_by_category": {},
                "file_reports": [],
                "duplication_clusters": [],
                "recommendations": [],
                "message": "No files available for detailed analysis."
            }
            self._last_summary = None
            logger.info("CodeQualityPlugin: no files available for detailed analysis")
            return
        
        # Perform full analysis
        quality_summary = QualitySummary()
        quality_summary.total_files = len(files_to_analyze)
        logger.debug(
            "CodeQualityPlugin analyzing %d files (project_root=%s)",
            len(files_to_analyze),
            self._project_root,
        )
        
        file_reports: List[FileQualityReport] = []
        all_issues: List[QualityIssue] = []
        total_lines = 0
        total_complexity = 0
        total_maintainability = 0.0
        
        for file_path in files_to_analyze:
            report = self._analyze_file(file_path)
            file_reports.append(report)
            all_issues.extend(report.issues)
            total_lines += report.lines_of_code
            total_complexity += report.complexity
            total_maintainability += report.maintainability_index
        
        quality_summary.total_lines = total_lines
        quality_summary.file_reports = file_reports
        
        # Averages
        if file_reports:
            quality_summary.average_complexity = total_complexity / len(file_reports)
            quality_summary.average_maintainability = total_maintainability / len(file_reports)
        
        # Duplication analysis
        duplications = find_duplications(files_to_analyze, chunk_size=self.duplication_chunk_size)
        for cluster in duplications:
            cluster.setdefault("source", "detector")
            cluster.setdefault("verification", None)
        duplications = self._apply_manual_links(duplications)
        quality_summary.duplication_clusters = duplications
        
        # Calculate duplication percentage
        duplicated_lines = 0
        for cluster in duplications:
            if cluster.get("source") == "manual":
                continue
            occurrences = cast(List[Dict[str, Any]], cluster.get("occurrences", []))
            if len(occurrences) > 1:
                # Count extra occurrences (first is original)
                for occ in occurrences[1:]:
                    code = str(occ.get("code_excerpt", ""))
                    duplicated_lines += len(code.split("\n"))
        
        quality_summary.duplication_percentage = (
            (duplicated_lines / total_lines * 100) if total_lines > 0 else 0.0
        )
        
        # Add duplication issues
        counted = 0
        for cluster in duplications:
            if counted >= 10:
                break
            if cluster.get("source") == "manual":
                continue
            occurrences = cast(List[Dict[str, Any]], cluster.get("occurrences", []))
            if len(occurrences) >= 2:
                locations = [f"{occ['path']}:{occ.get('line', '?')}" for occ in occurrences[:3]]
                all_issues.append(QualityIssue(
                    file=str(occurrences[0].get("path", "")),
                    line=occurrences[0].get("line"),
                    severity="warning" if len(occurrences) > 3 else "info",
                    category="duplication",
                    message=f"Code duplicated in {len(occurrences)} locations: {', '.join(locations)}",
                    suggestion="Extract duplicated code into a shared function or module."
                ))
                counted += 1
        
        # Count issues by severity and category
        quality_summary.total_issues = len(all_issues)
        quality_summary.issues_by_severity = {}
        quality_summary.issues_by_category = {}
        
        for issue in all_issues:
            quality_summary.issues_by_severity[issue.severity] = (
                quality_summary.issues_by_severity.get(issue.severity, 0) + 1
            )
            quality_summary.issues_by_category[issue.category] = (
                quality_summary.issues_by_category.get(issue.category, 0) + 1
            )
        
        # Calculate overall score
        # Start at 100, deduct points for issues
        score = 100.0
        
        # Complexity penalty
        avg_comp = quality_summary.average_complexity
        if avg_comp > self.complexity_threshold:
            score -= min(20, (avg_comp - self.complexity_threshold) * 0.5)
        
        # Duplication penalty
        dup_pct = quality_summary.duplication_percentage
        if dup_pct > DUPLICATION_THRESHOLDS["acceptable"]:
            score -= min(15, (dup_pct - DUPLICATION_THRESHOLDS["acceptable"]) * 2)
        
        # Issue penalties
        score -= quality_summary.issues_by_severity.get("error", 0) * 5
        score -= quality_summary.issues_by_severity.get("warning", 0) * 2
        score -= quality_summary.issues_by_severity.get("info", 0) * 0.5
        
        quality_summary.overall_score = max(0, min(100, score))
        quality_summary.overall_grade = self._get_overall_grade(quality_summary.overall_score)
        
        # Generate recommendations
        if avg_comp > self.complexity_threshold:
            quality_summary.recommendations.append(
                f"Average complexity ({avg_comp:.1f}) exceeds threshold ({self.complexity_threshold}). "
                "Consider breaking down complex functions."
            )
        
        if dup_pct > DUPLICATION_THRESHOLDS["warning"]:
            quality_summary.recommendations.append(
                f"Code duplication at {dup_pct:.1f}%. "
                "Extract repeated patterns into shared utilities."
            )
        
        if quality_summary.average_maintainability < 70:
            quality_summary.recommendations.append(
                "Overall maintainability is below optimal. "
                "Add documentation and simplify complex logic."
            )
        
        # Store for UI access
        self._last_summary = quality_summary
        
        # Add to summary
        summary["code_quality"] = quality_summary.to_dict()
        
        logger.info(
            "CodeQualityPlugin: analysis complete. Score: %.1f (%s), Issues: %d",
            quality_summary.overall_score,
            quality_summary.overall_grade,
            quality_summary.total_issues
        )
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("CodeQualityPlugin summary payload=%s", summary["code_quality"])

    def get_last_summary(self) -> Optional[QualitySummary]:
        """Get the last computed quality summary."""
        return self._last_summary

    # === Manual duplication linking helpers ===

    def _manual_links_path(self) -> Optional[Path]:
        if not self._project_root:
            return None
        if not self._manual_links_file or not str(self._manual_links_file).startswith(str(self._project_root)):
            self._manual_links_file = self._project_root / ".jupiter" / "manual_duplication_links.json"
        return self._manual_links_file

    def _load_manual_links_from_disk(self) -> List[dict[str, Any]]:
        path = self._manual_links_path()
        if not path or not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to read manual duplication links: %s", exc)
            return []

        if isinstance(payload, dict):
            links = payload.get("links", [])
        elif isinstance(payload, list):
            links = payload
        else:
            return []

        if not isinstance(links, list):
            return []

        for item in links:
            if isinstance(item, dict):
                item.setdefault("origin", "file")
        return cast(List[dict[str, Any]], links)

    def _write_manual_links_to_disk(self) -> None:
        path = self._manual_links_path()
        if not path:
            raise ValueError("Project root unknown; cannot persist manual links")
        file_links = [link.to_dict() for link in self.manual_links.values() if link.origin == "file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "links": file_links,
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _reload_manual_links(self) -> None:
        links: Dict[str, ManualDuplicationLink] = {}
        config_links = self.config.get("manual_duplication_links", []) if isinstance(self.config, dict) else []
        for entry in config_links:
            try:
                link = ManualDuplicationLink.from_dict(entry, origin="config")
                links[link.link_id] = link
            except ValueError as exc:
                logger.warning("Ignoring invalid manual duplication link from config: %s", exc)

        for entry in self._load_manual_links_from_disk():
            try:
                link = ManualDuplicationLink.from_dict(entry, origin="file")
                links[link.link_id] = link
            except ValueError as exc:
                logger.warning("Ignoring invalid manual duplication link from file: %s", exc)

        self.manual_links = links
        logger.debug(
            "CodeQualityPlugin reloaded %d manual duplication link(s)",
            len(self.manual_links),
        )

    def _normalize_code_block(self, code: str) -> str:
        lines = [line.rstrip() for line in code.splitlines()]
        return "\n".join(lines).strip()

    def _trim_excerpt(self, code: str, max_lines: int = 25) -> str:
        lines = code.splitlines()
        if len(lines) <= max_lines:
            return "\n".join(lines)
        return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"

    def _resolve_path(self, path_str: str) -> Optional[Path]:
        path = Path(path_str)
        if path.is_absolute():
            return path
        if not self._project_root:
            return None
        return (self._project_root / path_str).resolve()

    def _make_relative_path(self, path_str: str) -> str:
        path = Path(path_str)
        if self._project_root:
            try:
                return path.relative_to(self._project_root).as_posix()
            except ValueError:
                return path.as_posix()
        return path.as_posix()

    def _get_file_lines(self, file_path: Path) -> Optional[List[str]]:
        if not hasattr(self, "_manual_file_cache"):
            self._manual_file_cache: Dict[str, List[str]] = {}
        cache_key = str(file_path)
        if cache_key in self._manual_file_cache:
            return self._manual_file_cache[cache_key]
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError):
            return None
        self._manual_file_cache[cache_key] = lines
        return lines

    def _read_code_block(self, file_path: Path, start_line: int, end_line: int) -> Optional[str]:
        lines = self._get_file_lines(file_path)
        if lines is None:
            return None
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        if start_idx >= len(lines) or start_idx >= end_idx:
            return None
        return "".join(lines[start_idx:end_idx])

    def _build_manual_cluster(self, link: ManualDuplicationLink) -> Dict[str, Any]:
        self._manual_file_cache = {}
        occurrences_payload = []
        normalized_blocks = []
        issues: List[str] = []

        for occ in link.occurrences:
            resolved = self._resolve_path(occ.path)
            if not resolved or not resolved.exists():
                issues.append(f"Path missing: {occ.path}")
                continue
            code_excerpt = self._read_code_block(resolved, occ.start_line, occ.end_line)
            if code_excerpt is None:
                issues.append(f"Cannot read {resolved}:{occ.start_line}-{occ.end_line}")
                continue
            trimmed = self._trim_excerpt(code_excerpt)
            normalized_blocks.append(self._normalize_code_block(code_excerpt))
            occurrences_payload.append({
                "path": str(resolved),
                "line": occ.start_line,
                "end_line": occ.end_line,
                "function": occ.label,
                "code_excerpt": trimmed,
                "manual_label": occ.label,
            })

        if not occurrences_payload:
            status = "missing"
        else:
            unique_blocks = {block for block in normalized_blocks if block}
            if len(occurrences_payload) < len(link.occurrences):
                status = "missing"
            elif len(unique_blocks) <= 1:
                status = "verified"
            else:
                status = "diverged"

        cluster = {
            "hash": f"manual::{link.link_id}",
            "occurrences": occurrences_payload,
            "source": "manual",
            "manual_link_id": link.link_id,
            "manual_label": link.label,
            "manual_origin": link.origin,
            "verification": {
                "status": status,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "issues": issues,
            },
        }
        return cluster

    def _apply_manual_links(self, duplications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.manual_links:
            return duplications
        logger.debug(
            "CodeQualityPlugin applying %d manual link clusters",
            len(self.manual_links),
        )
        manual_clusters = []
        for link in self.manual_links.values():
            try:
                manual_clusters.append(self._build_manual_cluster(link))
            except Exception as exc:
                logger.error("Failed to build manual duplication cluster '%s': %s", link.link_id, exc)
        logger.debug(
            "CodeQualityPlugin appended %d manual clusters to %d detected ones",
            len(manual_clusters),
            len(duplications),
        )
        return duplications + manual_clusters

    def _generate_link_id(self, label: Optional[str]) -> str:
        base = None
        if label:
            base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
        if not base:
            base = "linked-block"
        candidate = base
        counter = 2
        while candidate in self.manual_links:
            candidate = f"{base}-{counter}"
            counter += 1
        return candidate

    def _update_summary_with_manual_cluster(self, cluster: Dict[str, Any]) -> None:
        if not self._last_summary:
            return
        existing = []
        for item in self._last_summary.duplication_clusters:
            if item.get("source") == "manual" and item.get("manual_link_id") == cluster.get("manual_link_id"):
                continue
            existing.append(item)
        existing.append(cluster)
        self._last_summary.duplication_clusters = existing

    def _remove_manual_cluster_from_summary(self, link_id: str) -> None:
        if not self._last_summary:
            return
        self._last_summary.duplication_clusters = [
            c for c in self._last_summary.duplication_clusters
            if not (c.get("source") == "manual" and c.get("manual_link_id") == link_id)
        ]

    def recheck_manual_links(self, link_id: Optional[str] = None) -> Dict[str, Any]:
        if not self.manual_links:
            return {"status": "empty", "links": []}
        if link_id and link_id not in self.manual_links:
            raise ValueError(f"Manual link '{link_id}' not found")
        targets = (
            [self.manual_links[link_id]]
            if link_id and link_id in self.manual_links
            else list(self.manual_links.values())
        )
        refreshed = []
        for link in targets:
            cluster = self._build_manual_cluster(link)
            refreshed.append(cluster)
            self._update_summary_with_manual_cluster(cluster)
        return {"status": "ok", "links": refreshed}

    def create_manual_link(self, label: Optional[str], cluster_hashes: List[str]) -> Dict[str, Any]:
        if not cluster_hashes or len(cluster_hashes) < 2:
            raise ValueError("Select at least two duplication clusters to link")
        if not self._last_summary:
            raise ValueError("No analysis data available. Run analyze first.")
        if not self._manual_links_path():
            raise ValueError("Project root unknown; cannot persist manual links yet")

        cluster_map = {
            c.get("hash"): c
            for c in self._last_summary.duplication_clusters
            if c.get("source") != "manual"
        }
        unique_hashes = list(dict.fromkeys(cluster_hashes))
        missing = [h for h in unique_hashes if h not in cluster_map]
        if missing:
            raise ValueError(f"Unknown cluster ids: {', '.join(missing)}")

        location_ranges: Dict[tuple[str, str], Dict[str, Any]] = {}
        for cluster_hash in unique_hashes:
            occurrences = cluster_map[cluster_hash].get("occurrences", [])
            for occ in occurrences:
                path = occ.get("path")
                if not path:
                    continue
                start = int(occ.get("line", 0))
                end = int(occ.get("end_line", start))
                if start == 0:
                    continue
                identifier = occ.get("function") or f"line:{start}"
                key = (path, identifier)
                entry = location_ranges.setdefault(key, {
                    "path": path,
                    "label": occ.get("function"),
                    "identifier": identifier,
                    "start": start,
                    "end": end,
                })
                entry["start"] = min(entry["start"], start)
                entry["end"] = max(entry["end"], end)

        if len(location_ranges) < 2:
            raise ValueError("Linked block must include at least two distinct occurrences")

        occurrences = [
            ManualLinkOccurrence(
                path=self._make_relative_path(entry["path"]),
                start_line=entry["start"],
                end_line=entry["end"],
                label=entry.get("label"),
            )
            for entry in location_ranges.values()
        ]

        link_id = self._generate_link_id(label)
        new_link = ManualDuplicationLink(link_id=link_id, label=label, occurrences=occurrences, origin="file")
        self.manual_links[link_id] = new_link
        self._write_manual_links_to_disk()
        cluster = self._build_manual_cluster(new_link)
        self._update_summary_with_manual_cluster(cluster)
        return cluster

    def delete_manual_link(self, link_id: str) -> None:
        link = self.manual_links.get(link_id)
        if not link:
            raise ValueError(f"Manual link '{link_id}' not found")
        if link.origin != "file":
            raise ValueError("Only links stored on disk can be removed via API")
        del self.manual_links[link_id]
        self._write_manual_links_to_disk()
        self._remove_manual_cluster_from_summary(link_id)

    # === UI Methods ===
    
    def get_ui_html(self) -> str:
        """Return HTML content for the Code Quality view."""
        return """
<div id="code-quality-view" class="view-content">
    <div class="view-header">
        <div>
            <h2 data-i18n="code_quality_title">Code Quality Analysis</h2>
            <p class="muted" data-i18n="code_quality_subtitle">Comprehensive analysis of complexity, duplication, and maintainability.</p>
        </div>
        <div class="view-actions">
            <button class="btn btn-secondary" data-action="export-quality">
                <span data-i18n="export_report">Export</span>
            </button>
            <button class="btn btn-primary" onclick="codeQualityRefresh()">
                <span data-i18n="refresh">Refresh</span>
            </button>
        </div>
    </div>
    
    <div id="quality-summary" class="quality-dashboard">
        <div class="quality-score-card">
            <div class="score-circle" id="quality-score">
                <span class="score-value">--</span>
                <span class="score-grade">-</span>
            </div>
            <div class="score-label" data-i18n="overall_score">Overall Score</div>
        </div>
        
        <div class="quality-metrics-grid">
            <div class="metric-card">
                <div class="metric-value" id="metric-files">--</div>
                <div class="metric-label" data-i18n="files_analyzed">Files Analyzed</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="metric-complexity">--</div>
                <div class="metric-label" data-i18n="avg_complexity">Avg Complexity</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="metric-duplication">--</div>
                <div class="metric-label" data-i18n="duplication">Duplication</div>
            </div>
            <div class="metric-card">
                <div class="metric-value" id="metric-issues">--</div>
                <div class="metric-label" data-i18n="total_issues">Total Issues</div>
            </div>
        </div>
    </div>
    
    <div class="quality-sections">
        <div class="section-tabs">
            <button class="tab-btn active" data-tab="dashboard" data-i18n="code_quality_dashboard_tab">Dashboard</button>
            <button class="tab-btn" data-tab="issues" data-i18n="issues_tab">Issues</button>
            <button class="tab-btn" data-tab="files" data-i18n="files_tab">Files</button>
            <button class="tab-btn" data-tab="duplication" data-i18n="duplication_tab">Duplication</button>
            <button class="tab-btn" data-tab="recommendations" data-i18n="recommendations_tab">Recommendations</button>
        </div>

        <div id="tab-dashboard" class="tab-content active">
            <div class="dashboard-intro">
                <div>
                    <p class="eyebrow" data-i18n="code_quality_dashboard_eyebrow">Synthèse</p>
                    <h3 data-i18n="quality_view">Qualité</h3>
                    <p class="muted" data-i18n="quality_subtitle">Métriques de qualité du code.</p>
                </div>
            </div>
            <div class="quality-dashboard-grid">
                <section class="quality-card">
                    <header>
                        <p class="eyebrow" data-i18n="q_complexity_eyebrow">Complexité</p>
                        <h4 data-i18n="q_complexity_title">Complexité Cyclomatique</h4>
                        <p class="muted small" data-i18n="q_complexity_subtitle">Estimation naïve basée sur les structures de contrôle.</p>
                    </header>
                    <div class="table-container">
                        <table class="quality-table" aria-describedby="q_complexity_title">
                            <thead>
                                <tr>
                                    <th data-i18n="th_file">Fichier</th>
                                    <th class="numeric" data-i18n="th_score">Score</th>
                                </tr>
                            </thead>
                            <tbody id="quality-complexity-body"></tbody>
                        </table>
                        <div id="quality-complexity-empty" class="empty-state" style="display: none;">
                            <p data-i18n="quality_empty">Aucune donnée de complexité.</p>
                        </div>
                    </div>
                </section>

                <section class="quality-card">
                    <header>
                        <p class="eyebrow" data-i18n="q_duplication_eyebrow">Duplication</p>
                        <h4 data-i18n="q_duplication_title">Code Dupliqué</h4>
                        <p class="muted small" data-i18n="q_duplication_subtitle">Clusters de code identique détectés.</p>
                    </header>
                    <div class="table-container">
                        <table class="quality-table" aria-describedby="q_duplication_title">
                            <thead>
                                <tr>
                                    <th data-i18n="th_hash">Hash</th>
                                    <th class="numeric" data-i18n="th_occurrences">Occurrences</th>
                                    <th data-i18n="th_details">Détails</th>
                                </tr>
                            </thead>
                            <tbody id="quality-duplication-body"></tbody>
                        </table>
                        <div id="quality-duplication-empty" class="empty-state" style="display: none;">
                            <p data-i18n="quality_empty">Aucune duplication détectée.</p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
        
        <div id="tab-issues" class="tab-content">
            <table class="data-table">
                <thead>
                    <tr>
                        <th data-i18n="severity">Severity</th>
                        <th data-i18n="category">Category</th>
                        <th data-i18n="file">File</th>
                        <th data-i18n="message">Message</th>
                    </tr>
                </thead>
                <tbody id="issues-tbody"></tbody>
            </table>
        </div>
        
        <div id="tab-files" class="tab-content">
            <table class="data-table">
                <thead>
                    <tr>
                        <th data-i18n="file">File</th>
                        <th data-i18n="complexity">Complexity</th>
                        <th data-i18n="grade">Grade</th>
                        <th data-i18n="lines">Lines</th>
                        <th data-i18n="maintainability">Maintainability</th>
                    </tr>
                </thead>
                <tbody id="files-tbody"></tbody>
            </table>
        </div>
        
        <div id="tab-duplication" class="tab-content">
            <div class="duplication-toolbar">
                <div class="dup-buttons">
                    <button class="btn btn-secondary btn-small" id="link-selected-btn" onclick="codeQualityLinkSelected()" disabled>Link Selected</button>
                    <button class="btn btn-ghost btn-small" id="recheck-links-btn" onclick="codeQualityRecheckManualLinks()">Re-check Linked Blocks</button>
                </div>
                <p class="muted small">Select overlapping detector clusters and merge them into a single, verifiable block. Linked blocks are revalidated whenever you refresh.</p>
            </div>
            <div id="duplication-list" class="duplication-clusters"></div>
        </div>
        
        <div id="tab-recommendations" class="tab-content">
            <ul id="recommendations-list" class="recommendations"></ul>
        </div>
    </div>
</div>

<style>
.quality-dashboard {
    display: flex;
    gap: 2rem;
    align-items: center;
    padding: 1.5rem;
    background: var(--bg-secondary);
    border-radius: 8px;
    margin-bottom: 1.5rem;
}

.quality-score-card {
    text-align: center;
    min-width: 150px;
}

.score-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: conic-gradient(var(--accent-color) var(--score-pct, 0%), var(--bg-tertiary) 0);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 0 auto 0.5rem;
    position: relative;
}

.score-circle::before {
    content: '';
    position: absolute;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    background: var(--bg-secondary);
}

.score-value, .score-grade {
    position: relative;
    z-index: 1;
}

.score-value {
    font-size: 1.8rem;
    font-weight: bold;
    color: var(--text-primary);
}

.score-grade {
    font-size: 1.2rem;
    color: var(--accent-color);
}

.score-label {
    color: var(--text-secondary);
    font-size: 0.9rem;
}

.quality-metrics-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    flex: 1;
}

.metric-card {
    background: var(--bg-tertiary);
    padding: 1rem;
    border-radius: 6px;
    text-align: center;
}

.metric-value {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--text-primary);
}

.metric-label {
    color: var(--text-secondary);
    font-size: 0.8rem;
    margin-top: 0.25rem;
}

.section-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.5rem;
}

.tab-btn {
    background: transparent;
    border: none;
    padding: 0.5rem 1rem;
    color: var(--text-secondary);
    cursor: pointer;
    border-radius: 4px 4px 0 0;
    transition: all 0.2s;
}

.tab-btn:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

.tab-btn.active {
    background: var(--accent-color);
    color: white;
}

.tab-content {
    display: none;
}

.tab-content.active {
    display: block;
}

.severity-error { color: #ff5555; }
.severity-warning { color: #ffaa00; }
.severity-info { color: #5599ff; }

.grade-A { color: #22cc66; }
.grade-B { color: #88cc22; }
.grade-C { color: #ccaa00; }
.grade-D { color: #ff8800; }
.grade-F { color: #ff4444; }

.duplication-clusters {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.dup-cluster {
    background: var(--bg-secondary);
    border-radius: 6px;
    padding: 1rem;
    border-left: 3px solid var(--accent-color);
}

.dup-cluster.manual-cluster {
    border-left-color: #f2b705;
}

.duplication-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
}

.dup-buttons {
    display: flex;
    gap: 0.5rem;
}

.btn-small {
    padding: 0.35rem 0.75rem;
    font-size: 0.85rem;
}

.btn-ghost {
    border: 1px solid var(--border-color);
    background: transparent;
    color: var(--text-secondary);
}

.dup-cluster-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.5rem;
}

.dup-cluster-title {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    align-items: center;
}

.dup-label {
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.dup-select {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.8rem;
    color: var(--text-secondary);
}

.badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.1rem 0.6rem;
    font-size: 0.75rem;
    background: var(--bg-tertiary);
    color: var(--text-main);
}

.manual-badge {
    background: rgba(242, 183, 5, 0.2);
    color: #f2b705;
}

.status-badge {
    text-transform: capitalize;
}

.status-verified {
    background: rgba(76, 175, 80, 0.2);
    color: #4caf50;
}

.status-diverged {
    background: rgba(244, 67, 54, 0.2);
    color: #f44336;
}

.status-missing {
    background: rgba(255, 193, 7, 0.2);
    color: #ffc107;
}

.dup-manual-actions {
    display: flex;
    gap: 0.4rem;
}

button.ghost.small {
    border: 1px solid var(--border-color);
    background: transparent;
    color: var(--text-secondary);
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    cursor: pointer;
}

button.ghost.small:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.dup-locations {
    margin: 0.5rem 0;
    padding-left: 1rem;
}

.dup-code {
    background: var(--bg-tertiary);
    padding: 0.5rem;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.85rem;
    white-space: pre-wrap;
    max-height: 150px;
    overflow-y: auto;
}

.recommendations {
    list-style: none;
    padding: 0;
}

.recommendations li {
    padding: 1rem;
    background: var(--bg-secondary);
    border-radius: 6px;
    margin-bottom: 0.5rem;
    border-left: 3px solid var(--accent-color);
}

.recommendations li::before {
    content: '💡 ';
}

.dashboard-intro {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.quality-dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.2rem;
}

.quality-card {
    background: var(--bg-secondary);
    border-radius: 8px;
    padding: 1rem;
    display: flex;
    flex-direction: column;
}

.quality-card header {
    margin-bottom: 0.75rem;
}

.quality-card .table-container {
    flex: 1;
}

.quality-table {
    width: 100%;
    border-collapse: collapse;
}

.quality-table th,
.quality-table td {
    padding: 0.4rem 0.25rem;
    border-bottom: 1px solid var(--border-color);
    text-align: left;
}

.quality-table th.numeric,
.quality-table td.numeric {
    text-align: right;
}

.quality-table td.truncate {
    max-width: 240px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.quality-card .empty-state {
    padding: 0.75rem;
    text-align: center;
    color: var(--text-secondary);
}
</style>
"""

    def get_ui_js(self) -> str:
        """Return JavaScript code for the Code Quality view."""
        return """
// Code Quality Plugin JavaScript

window.codeQualityData = null;

function resolveCodeQualityApiBase() {
    if (window.state && state.apiBaseUrl) {
        console.debug('[CodeQuality] Using state.apiBaseUrl:', state.apiBaseUrl);
        return state.apiBaseUrl;
    }
    if (typeof inferApiBaseUrl === 'function') {
        try {
            const inferred = inferApiBaseUrl();
            if (inferred) {
                console.debug('[CodeQuality] inferApiBaseUrl returned:', inferred);
                return inferred;
            }
        } catch (err) {
            console.warn('[CodeQuality] inferApiBaseUrl failed:', err);
        }
    }
    const origin = window.location.origin.replace(/[/]$/, '');
    console.debug('[CodeQuality] Falling back to window.origin:', origin);
    if (origin.includes(':8050')) {
        return origin.replace(':8050', ':8000');
    }
    return origin || 'http://127.0.0.1:8000';
}

function buildCodeQualityHeaders() {
    const headers = { 'Accept': 'application/json' };
    const token = (window.state && state.token)
        || localStorage.getItem('jupiter-token')
        || sessionStorage.getItem('jupiter-token');
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }
    return headers;
}

async function codeQualityRefresh() {
    console.log('[CodeQuality] Refreshing data...');
    const apiBase = resolveCodeQualityApiBase();
    const requestOptions = { headers: buildCodeQualityHeaders() };
    const url = `${apiBase}/analyze`;
    console.log('[CodeQuality] Fetch URL:', url);

    try {
        let resp;
        if (typeof apiFetch === 'function') {
            resp = await apiFetch(url, requestOptions);
        } else {
            resp = await fetch(url, requestOptions);
            if (resp.status === 401) {
                throw new Error('Unauthorized');
            }
        }

        console.log('[CodeQuality] Response status:', resp.status);

        if (!resp.ok) {
            const error = await resp.json().catch(() => ({ detail: 'Unknown error' }));
            console.error('[CodeQuality] Response not OK:', resp.status, error);
            codeQualityRender({ status: 'error', message: error.detail || `HTTP ${resp.status}` });
            return;
        }

        const data = await resp.json();
        console.log('[CodeQuality] Response:', data);

        if (data.code_quality) {
            console.log('[CodeQuality] Found code_quality data:', data.code_quality);
            window.codeQualityData = data.code_quality;
            codeQualityRender(data.code_quality);
        } else {
            console.warn('[CodeQuality] No code_quality in response. Keys:', Object.keys(data));
            codeQualityRender({ status: 'no_data', message: 'Run a scan first to generate quality data.' });
        }
    } catch (err) {
        console.error('[CodeQuality] Failed to refresh:', err);
        const message = err && err.message ? err.message : 'Unknown error';
        const hint = message === 'Failed to fetch' ? 'Ensure the Jupiter API server is running on port 8000.' : '';
        codeQualityRender({ status: 'error', message: `Failed to load data: ${message}. ${hint}`.trim() });
    }
}

function codeQualityRender(data) {
    console.log('[CodeQuality] Rendering data:', data);
    
    const scoreEl = document.getElementById('quality-score');
    const metricFiles = document.getElementById('metric-files');
    const metricComplexity = document.getElementById('metric-complexity');
    const metricDuplication = document.getElementById('metric-duplication');
    const metricIssues = document.getElementById('metric-issues');
    const dashComplexityBody = document.getElementById('quality-complexity-body');
    const dashComplexityEmpty = document.getElementById('quality-complexity-empty');
    const dashDupBody = document.getElementById('quality-duplication-body');
    const dashDupEmpty = document.getElementById('quality-duplication-empty');

    if (dashComplexityBody) dashComplexityBody.innerHTML = '';
    if (dashDupBody) dashDupBody.innerHTML = '';
    if (dashComplexityEmpty) dashComplexityEmpty.style.display = 'block';
    if (dashDupEmpty) dashDupEmpty.style.display = 'block';
    
    if (!data || data.status === 'no_files' || data.status === 'no_data' || data.status === 'error') {
        if (scoreEl) {
            scoreEl.innerHTML = '<span class="score-value">--</span><span class="score-grade">-</span>';
            scoreEl.style.setProperty('--score-pct', '0%');
        }
        if (metricFiles) metricFiles.textContent = '--';
        if (metricComplexity) metricComplexity.textContent = '--';
        if (metricDuplication) metricDuplication.textContent = '--';
        if (metricIssues) metricIssues.textContent = '--';
        if (dashComplexityEmpty) dashComplexityEmpty.style.display = 'block';
        if (dashDupEmpty) dashDupEmpty.style.display = 'block';
        
        // Show message in recommendations
        const recList = document.getElementById('recommendations-list');
        if (recList) {
            recList.innerHTML = '<li>' + (data?.message || 'No data available. Run a scan first.') + '</li>';
        }
        return;
    }
    
    // Update score circle
    const score = data.overall_score || 0;
    const grade = data.overall_grade || '-';
    if (scoreEl) {
        scoreEl.innerHTML = `<span class="score-value">${Math.round(score)}</span><span class="score-grade">${grade}</span>`;
        scoreEl.style.setProperty('--score-pct', score + '%');
    }
    
    // Update metrics
    if (metricFiles) metricFiles.textContent = data.total_files || 0;
    if (metricComplexity) metricComplexity.textContent = (data.average_complexity || 0).toFixed(1);
    if (metricDuplication) metricDuplication.textContent = (data.duplication_percentage || 0).toFixed(1) + '%';
    if (metricIssues) metricIssues.textContent = data.total_issues || 0;
    
    if (dashComplexityBody) {
        const sortedFiles = (data.file_reports || [])
            .filter(Boolean)
            .sort((a, b) => (b.complexity || 0) - (a.complexity || 0))
            .slice(0, 10);
        if (sortedFiles.length === 0) {
            if (dashComplexityEmpty) dashComplexityEmpty.style.display = 'block';
        } else {
            if (dashComplexityEmpty) dashComplexityEmpty.style.display = 'none';
            sortedFiles.forEach(file => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="truncate" title="${file.path || ''}">${file.path || '—'}</td>
                    <td class="numeric">${file.complexity ?? 0}</td>
                `;
                dashComplexityBody.appendChild(row);
            });
        }
    }

    if (dashDupBody) {
        const clusters = Array.isArray(data.duplication_clusters) ? data.duplication_clusters.slice(0, 10) : [];
        if (clusters.length === 0) {
            if (dashDupEmpty) dashDupEmpty.style.display = 'block';
        } else {
            if (dashDupEmpty) dashDupEmpty.style.display = 'none';
            clusters.forEach(cluster => {
                const row = document.createElement('tr');
                const occs = Array.isArray(cluster.occurrences) ? cluster.occurrences : [];
                const locations = occs.map(occ => {
                    const fileName = occ.path || '—';
                    const start = occ.line ?? occ.start_line ?? '?';
                    const end = occ.end_line && occ.end_line !== start ? `-${occ.end_line}` : '';
                    return `${fileName}:${start}${end}`;
                }).join(', ');
                const hash = (cluster.hash || cluster.manual_link_id || 'manual').toString();
                row.innerHTML = `
                    <td class="mono small">${hash.substring(0, 8)}</td>
                    <td class="numeric">${occs.length}</td>
                    <td class="small truncate" title="${locations}">${locations || '—'}</td>
                `;
                dashDupBody.appendChild(row);
            });
        }
    }
    
    // Render issues
    const issuesTbody = document.getElementById('issues-tbody');
    if (issuesTbody) {
        issuesTbody.innerHTML = '';
        
        const allIssues = [];
        (data.file_reports || []).forEach(file => {
            (file.issues || []).forEach(issue => {
                allIssues.push(issue);
            });
        });
        
        if (allIssues.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="4" style="text-align: center; color: var(--text-secondary);">No issues found</td>';
            issuesTbody.appendChild(tr);
        } else {
            allIssues.forEach(issue => {
                const tr = document.createElement('tr');
                const fileName = (issue.file || '').split(/[\\\\/]/).pop() || 'Unknown';
                tr.innerHTML = `
                    <td><span class="severity-${issue.severity}">${(issue.severity || '').toUpperCase()}</span></td>
                    <td>${issue.category || ''}</td>
                    <td title="${issue.file || ''}">${fileName}</td>
                    <td>${issue.message || ''}</td>
                `;
                issuesTbody.appendChild(tr);
            });
        }
    }
    
    // Render files
    const filesTbody = document.getElementById('files-tbody');
    if (filesTbody) {
        filesTbody.innerHTML = '';
        
        const fileReports = (data.file_reports || []).sort((a, b) => (b.complexity || 0) - (a.complexity || 0));
        
        if (fileReports.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="5" style="text-align: center; color: var(--text-secondary);">No files analyzed</td>';
            filesTbody.appendChild(tr);
        } else {
            fileReports.forEach(file => {
                const tr = document.createElement('tr');
                const fileName = (file.path || '').split(/[\\\\/]/).pop() || 'Unknown';
                tr.innerHTML = `
                    <td title="${file.path || ''}">${fileName}</td>
                    <td>${file.complexity || 0}</td>
                    <td><span class="grade-${file.complexity_grade || 'A'}">${file.complexity_grade || 'A'}</span></td>
                    <td>${file.lines_of_code || 0}</td>
                    <td>${(file.maintainability_index || 0).toFixed(1)}</td>
                `;
                filesTbody.appendChild(tr);
            });
        }
    }
    
    // Render duplication
    const dupList = document.getElementById('duplication-list');
    if (dupList) {
        dupList.innerHTML = '';
        const linkBtn = document.getElementById('link-selected-btn');
        if (linkBtn) {
            linkBtn.disabled = true;
        }
        const clusters = data.duplication_clusters || [];
        if (clusters.length === 0) {
            dupList.innerHTML = '<p style="color: var(--text-secondary);">No code duplication detected. Great job!</p>';
        } else {
            clusters.slice(0, 15).forEach((cluster, idx) => {
                const div = document.createElement('div');
                const isManual = cluster.source === 'manual';
                const occurrences = cluster.occurrences || [];
                const locationLabels = occurrences.map(occ => {
                    const fileName = (occ.path || '').split(/[\\\\/]/).pop() || 'Unknown';
                    const startLine = occ.line || '?';
                    const endLine = occ.end_line && occ.end_line !== occ.line ? `-${occ.end_line}` : '';
                    const fn = occ.function ? ` (${occ.function})` : '';
                    return `${fileName}:${startLine}${endLine}${fn}`;
                }).join(', ');
                const code = occurrences[0]?.code_excerpt || '';
                const manualLabel = cluster.manual_label ? `<span class="dup-label">${escapeHtml(cluster.manual_label)}</span>` : '';
                const checkboxHtml = isManual ? '' : `
                    <label class="dup-select">
                        <input type="checkbox" class="dup-select-checkbox" data-hash="${cluster.hash}">
                        <span>Select</span>
                    </label>`;
                const verification = cluster.verification || {};
                const status = (verification.status || 'pending').toString();
                const statusBadge = isManual ? `<span class="badge status-badge status-${status}">${status.toUpperCase()}</span>` : '';
                const manualBadge = isManual ? '<span class="badge manual-badge">Linked</span>' : '';
                const manualActions = (isManual && cluster.manual_link_id) ? `
                    <div class="dup-manual-actions">
                        <button class="ghost small" onclick="codeQualityRecheckLink('${cluster.manual_link_id}')">Re-check</button>
                        <button class="ghost small" ${cluster.manual_origin !== 'file' ? 'disabled title="Defined in config"' : ''} onclick="codeQualityDeleteManualLink('${cluster.manual_link_id}')">Remove</button>
                    </div>` : '';
                const headerActions = checkboxHtml || manualActions;
                div.className = 'dup-cluster' + (isManual ? ' manual-cluster' : '');
                div.innerHTML = `
                    <div class="dup-cluster-header">
                        <div class="dup-cluster-title">
                            <strong>Cluster ${idx + 1}</strong>
                            ${manualBadge}
                            ${statusBadge}
                            ${manualLabel}
                        </div>
                        ${headerActions}
                    </div>
                    <div class="dup-locations">${escapeHtml(locationLabels)}</div>
                    <pre class="dup-code">${escapeHtml(code)}</pre>
                `;
                dupList.appendChild(div);
            });
            codeQualityAttachSelectionHandlers();
        }
    }
    
    // Render recommendations
    const recList = document.getElementById('recommendations-list');
    if (recList) {
        recList.innerHTML = '';
        
        const recs = data.recommendations || [];
        
        if (recs.length === 0) {
            const li = document.createElement('li');
            li.textContent = 'No recommendations. Code quality looks good!';
            recList.appendChild(li);
        } else {
            recs.forEach(rec => {
                const li = document.createElement('li');
                li.textContent = rec;
                recList.appendChild(li);
            });
        }
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function codeQualityAttachSelectionHandlers() {
    const checkboxes = document.querySelectorAll('.dup-select-checkbox');
    checkboxes.forEach(cb => cb.addEventListener('change', codeQualityUpdateLinkButtonState));
    codeQualityUpdateLinkButtonState();
}

function codeQualityUpdateLinkButtonState() {
    const btn = document.getElementById('link-selected-btn');
    if (!btn) return;
    const selected = document.querySelectorAll('.dup-select-checkbox:checked').length;
    btn.disabled = selected < 2;
}

function codeQualitySelectedClusterHashes() {
    return Array.from(document.querySelectorAll('.dup-select-checkbox:checked')).map(cb => cb.dataset.hash);
}

function codeQualityNotify(message, type = 'info') {
    if (typeof showNotification === 'function') {
        showNotification(message, type);
    } else {
        console.log(`[CodeQuality] ${type}: ${message}`);
    }
}

async function codeQualitySendRequest(method, path, body) {
    const apiBaseRaw = resolveCodeQualityApiBase() || '';
    const apiBase = apiBaseRaw.endsWith('/') ? apiBaseRaw.slice(0, -1) : apiBaseRaw;
    const headers = buildCodeQualityHeaders();
    if (body !== undefined) {
        headers['Content-Type'] = 'application/json';
    }
    const response = await fetch(`${apiBase}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    if (response.status === 204) {
        return {};
    }
    return response.json();
}

async function codeQualityLinkSelected() {
    const hashes = codeQualitySelectedClusterHashes();
    if (hashes.length < 2) {
        codeQualityNotify('Select at least two detector clusters first.', 'warning');
        return;
    }
    const label = prompt('Label for the linked block (optional):', '') || undefined;
    try {
        await codeQualitySendRequest('POST', '/plugins/code_quality/manual-links', { hashes, label });
        codeQualityNotify('Linked block created.', 'success');
        await codeQualityRefresh();
    } catch (err) {
        codeQualityNotify(`Failed to link clusters: ${err.message}`, 'error');
    }
}

async function codeQualityRecheckManualLinks(linkId) {
    try {
        await codeQualitySendRequest('POST', '/plugins/code_quality/manual-links/recheck', linkId ? { link_id: linkId } : {});
        codeQualityNotify('Manual links rechecked.', 'success');
        await codeQualityRefresh();
    } catch (err) {
        codeQualityNotify(`Failed to recheck links: ${err.message}`, 'error');
    }
}

function codeQualityRecheckLink(linkId) {
    return codeQualityRecheckManualLinks(linkId);
}

async function codeQualityDeleteManualLink(linkId) {
    if (!confirm('Remove this linked duplication block?')) {
        return;
    }
    try {
        await codeQualitySendRequest('DELETE', `/plugins/code_quality/manual-links/${linkId}`);
        codeQualityNotify('Linked block removed.', 'success');
        await codeQualityRefresh();
    } catch (err) {
        codeQualityNotify(`Failed to remove linked block: ${err.message}`, 'error');
    }
}

function setupCodeQualityTabs() {
    const view = document.getElementById('code-quality-view');
    if (!view) return;
    view.querySelectorAll('.section-tabs .tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            view.querySelectorAll('.section-tabs .tab-btn').forEach(b => b.classList.remove('active'));
            view.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const target = view.querySelector('#tab-' + btn.dataset.tab);
            if (target) target.classList.add('active');
        });
    });
}

window.code_qualityView = {
    init() {
        setupCodeQualityTabs();
        codeQualityRefresh();
    },
    refresh: codeQualityRefresh
};
"""

    def get_settings_html(self) -> str:
        """Return HTML for the settings section."""
        return """
<section class="plugin-settings code-quality-settings" id="code-quality-settings">
    <header class="plugin-settings-header">
        <div>
            <p class="eyebrow" data-i18n="code_quality_view">Qualité du Code</p>
            <h3 data-i18n="code_quality_settings">Code Quality Settings</h3>
            <p class="muted small" data-i18n="code_quality_settings_hint">Ajustez la profondeur de l'analyse et les seuils d'alerte utilisés par le plugin.</p>
        </div>
        <label class="toggle-setting">
            <input type="checkbox" id="cq-enabled">
            <span data-i18n="cq_enabled">Enable Code Quality Analysis</span>
        </label>
    </header>
    <div class="settings-grid code-quality-grid">
        <div class="setting-item">
            <label for="cq-max-files" data-i18n="cq_max_files">Maximum Files to Analyze</label>
            <input type="number" id="cq-max-files" value="200" min="10" max="1000">
            <p class="setting-hint" data-i18n="cq_max_files_hint">Limite haute pour garder l'analyse rapide; augmentez-la pour de gros monorepos.</p>
        </div>
        <div class="setting-item">
            <label for="cq-complexity-threshold" data-i18n="cq_complexity_threshold">Complexity Warning Threshold</label>
            <input type="number" id="cq-complexity-threshold" value="15" min="5" max="50">
            <p class="setting-hint" data-i18n="cq_complexity_threshold_hint">Au-delà de ce score, les fichiers passent en alerte orange/rouge.</p>
        </div>
        <div class="setting-item">
            <label for="cq-dup-chunk" data-i18n="cq_dup_chunk">Duplication Chunk Size</label>
            <input type="number" id="cq-dup-chunk" value="6" min="3" max="20">
            <p class="setting-hint" data-i18n="cq_dup_chunk_hint">Nombre de lignes par bloc pour détecter les clones. Plus petit = plus sensible.</p>
        </div>
        <div class="setting-item">
            <label class="checkbox-label" for="cq-include-tests">
                <input type="checkbox" id="cq-include-tests">
                <span data-i18n="cq_include_tests">Include Test Files</span>
            </label>
            <p class="setting-hint" data-i18n="cq_include_tests_hint">Inclut les répertoires `tests/` et `__tests__` dans les métriques.</p>
        </div>
    </div>
    <footer class="plugin-settings-footer">
        <button class="btn btn-primary" id="cq-save-btn" data-i18n="save">Save</button>
        <span class="setting-result" id="cq-settings-status">&nbsp;</span>
    </footer>
</section>

<script>
(function() {
    const codeQualitySettings = {
        getApiBaseUrl() {
            if (window.state?.apiBaseUrl) {
                return state.apiBaseUrl;
            }
            const origin = window.location?.origin || '';
            if (origin.includes(':8050')) {
                return origin.replace(':8050', ':8000');
            }
            return origin || 'http://127.0.0.1:8000';
        },
        getToken() {
            if (window.state?.token) {
                return state.token;
            }
            return localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        },
        notify(message, type = 'info') {
            if (typeof window.showNotification === 'function') {
                window.showNotification(message, type, {
                    title: 'Code Quality',
                    icon: type === 'error' ? '⚠️' : '📊'
                });
            } else {
                console[type === 'error' ? 'error' : 'log']('[CodeQuality]', message);
            }
        },
        buildOptions(options = {}) {
            const opts = { ...options };
            const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
            const token = this.getToken();
            if (token && !headers.Authorization) {
                headers.Authorization = `Bearer ${token}`;
            }
            if (opts.body && typeof opts.body !== 'string' && !(opts.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(opts.body);
            }
            opts.headers = headers;
            return opts;
        },
        async request(path, options = {}) {
            const url = path.startsWith('http') ? path : `${this.getApiBaseUrl()}${path}`;
            return fetch(url, this.buildOptions(options));
        },
        setStatus(text = '', variant = null) {
            const statusEl = document.getElementById('cq-settings-status');
            if (!statusEl) return;
            statusEl.textContent = text;
            statusEl.className = 'setting-result';
            if (variant === 'error') {
                statusEl.classList.add('error');
            } else if (variant === 'success') {
                statusEl.classList.add('ok');
            } else if (variant === 'busy') {
                statusEl.classList.add('busy');
            }
        },
        readPayload() {
            return {
                enabled: document.getElementById('cq-enabled').checked,
                max_files: parseInt(document.getElementById('cq-max-files').value, 10) || 200,
                complexity_threshold: parseInt(document.getElementById('cq-complexity-threshold').value, 10) || 15,
                duplication_chunk_size: parseInt(document.getElementById('cq-dup-chunk').value, 10) || 6,
                include_tests: document.getElementById('cq-include-tests').checked,
            };
        },
        async load() {
            this.setStatus('Loading...', 'busy');
            try {
                const resp = await this.request('/plugins/code_quality/config');
                if (!resp.ok) {
                    throw new Error(`HTTP ${resp.status}`);
                }
                const config = await resp.json() || {};
                document.getElementById('cq-enabled').checked = config.enabled !== false;
                document.getElementById('cq-max-files').value = config.max_files ?? 200;
                document.getElementById('cq-complexity-threshold').value = config.complexity_threshold ?? 15;
                document.getElementById('cq-dup-chunk').value = config.duplication_chunk_size ?? 6;
                document.getElementById('cq-include-tests').checked = Boolean(config.include_tests);
                this.setStatus('', null);
            } catch (err) {
                console.error('[CodeQuality] Failed to load settings:', err);
                this.setStatus('Error', 'error');
                this.notify('Failed to load Code Quality settings', 'error');
            }
        },
        async save() {
            const button = document.getElementById('cq-save-btn');
            if (button) button.disabled = true;
            this.setStatus('Saving...', 'busy');
            try {
                const resp = await this.request('/plugins/code_quality/config', {
                    method: 'POST',
                    body: this.readPayload(),
                });
                if (!resp.ok) {
                    throw new Error(`HTTP ${resp.status}`);
                }
                this.setStatus('Saved', 'success');
                this.notify('Code Quality settings saved', 'success');
            } catch (err) {
                console.error('[CodeQuality] Failed to save settings:', err);
                this.setStatus('Error', 'error');
                this.notify('Failed to save Code Quality settings', 'error');
            } finally {
                if (button) button.disabled = false;
            }
        },
        bind() {
            document.getElementById('cq-save-btn')?.addEventListener('click', (event) => {
                event.preventDefault();
                this.save();
            });
        },
        init() {
            this.bind();
            this.load();
        }
    };

    window.codeQualitySettings = codeQualitySettings;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => codeQualitySettings.init());
    } else {
        codeQualitySettings.init();
    }
})();
</script>

<style>
#code-quality-settings .code-quality-grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}
#code-quality-settings .setting-item {
    border: 1px solid var(--border);
    background: var(--panel-contrast);
}
#code-quality-settings .setting-result {
    min-width: 2rem;
    text-align: center;
}
</style>
"""
