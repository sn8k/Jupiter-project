"""
Code Quality Plugin - Analyzer
==============================

Main analyzer class for code quality metrics.

Version: 0.8.1
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, cast

from jupiter.plugins.code_quality.core.models import (
    QualityIssue,
    FileQualityReport,
    QualitySummary,
    ManualLinkOccurrence,
    ManualDuplicationLink,
)

logger = logging.getLogger(__name__)

# Thresholds
COMPLEXITY_THRESHOLDS = {
    "low": 10,
    "moderate": 20,
    "high": 30,
    "very_high": 50
}

DUPLICATION_THRESHOLDS = {
    "acceptable": 3,
    "warning": 5,
    "high": 10
}


class CodeQualityAnalyzer:
    """Comprehensive code quality analysis."""

    def __init__(self) -> None:
        self.enabled = True
        self.max_files = 200
        self.complexity_threshold = 15
        self.duplication_chunk_size = 6
        self.include_tests = False
        self._last_summary: Optional[QualitySummary] = None
        self._project_root: Optional[Path] = None
        self.config: dict[str, Any] = {}
        self.manual_links: dict[str, ManualDuplicationLink] = {}
        self._manual_links_file: Optional[Path] = None
        self._manual_file_cache: dict[str, list[str]] = {}

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the analyzer."""
        self.config = config
        self.enabled = config.get("enabled", True)
        self.max_files = config.get("max_files", 200)
        self.complexity_threshold = config.get("complexity_threshold", 15)
        self.duplication_chunk_size = config.get("duplication_chunk_size", 6)
        self.include_tests = config.get("include_tests", False)
        self._reload_manual_links()
        logger.info(
            "CodeQualityAnalyzer configured: enabled=%s, max_files=%d, threshold=%d",
            self.enabled, self.max_files, self.complexity_threshold
        )

    def get_config(self) -> dict[str, Any]:
        """Return current configuration."""
        return {
            "enabled": self.enabled,
            "max_files": self.max_files,
            "complexity_threshold": self.complexity_threshold,
            "duplication_chunk_size": self.duplication_chunk_size,
            "include_tests": self.include_tests,
        }

    def get_last_summary(self) -> Optional[QualitySummary]:
        """Get the last computed quality summary."""
        return self._last_summary

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
        """Calculate maintainability index (0-100)."""
        if lines_of_code == 0:
            return 100.0
        
        base = 100.0
        
        if complexity > self.complexity_threshold:
            base -= (complexity - self.complexity_threshold) * 0.5
        
        if lines_of_code > 200:
            base -= min(20, 5 * math.log10(lines_of_code / 200))
        
        if comment_ratio > 0.05:
            base += min(5, comment_ratio * 25)
        
        return max(0, min(100, base))

    def _analyze_file(self, file_path: Path) -> FileQualityReport:
        """Analyze a single file for quality metrics."""
        from jupiter.core.quality.complexity import estimate_complexity, estimate_js_complexity
        
        path_str = str(file_path)
        report = FileQualityReport(path=path_str)
        
        suffix = file_path.suffix.lower()
        is_python = suffix == ".py"
        is_js_ts = suffix in (".js", ".ts", ".jsx", ".tsx")
        
        if not (is_python or is_js_ts):
            return report
        
        total_lines, comment_lines = self._count_lines_and_comments(file_path)
        report.lines_of_code = total_lines
        report.comment_ratio = comment_lines / total_lines if total_lines > 0 else 0.0
        
        if is_python:
            report.complexity = estimate_complexity(file_path)
        else:
            report.complexity = estimate_js_complexity(file_path)
        
        report.complexity_grade = self._get_complexity_grade(report.complexity)
        
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

    def _filter_files(self, files: list[dict[str, Any]]) -> list[Path]:
        """Filter files for analysis based on configuration."""
        result = []
        
        for file_info in files:
            path_str = file_info.get("path", "")
            if not path_str:
                continue
            
            path = Path(path_str)
            suffix = path.suffix.lower()
            
            if suffix not in (".py", ".js", ".ts", ".jsx", ".tsx"):
                continue
            
            if not self.include_tests:
                name_lower = path.name.lower()
                path_lower = str(path).lower()
                if any(pattern in name_lower or pattern in path_lower for pattern in 
                       ["test_", "_test", "tests/", "test/", ".test.", ".spec."]):
                    continue
            
            result.append(path)

        return result[:self.max_files]

    def on_scan(self, report: dict[str, Any]) -> None:
        """Add quality metrics to the scan report."""
        from jupiter.core.quality.complexity import estimate_complexity, estimate_js_complexity
        
        if not self.enabled:
            return
        
        logger.info("CodeQualityAnalyzer: analyzing scan report...")
        
        files = report.get("files", [])
        if not files:
            report["code_quality"] = {
                "status": "no_files",
                "message": "No files to analyze."
            }
            return
        
        project_path = report.get("project_path")
        if project_path:
            self._project_root = Path(project_path)
            self._reload_manual_links()
        
        files_to_analyze = self._filter_files(files)
        
        if not files_to_analyze:
            report["code_quality"] = {
                "status": "no_analyzable_files",
                "message": "No Python or JS/TS files found for analysis."
            }
            return
        
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
        
        logger.info("CodeQualityAnalyzer: scan analysis complete. %d files, avg complexity: %.1f",
                    len(files_to_analyze), avg_complexity)

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """Add comprehensive quality metrics to the analysis summary."""
        from jupiter.core.quality.duplication import find_duplications
        
        if not self.enabled:
            return
        
        logger.info("CodeQualityAnalyzer: performing full quality analysis...")
        
        # Try to get project root from various sources
        if not self._project_root:
            hotspots = summary.get("hotspots", {})
            if isinstance(hotspots, dict):
                for category_items in hotspots.values():
                    if isinstance(category_items, list) and category_items:
                        first_item = category_items[0]
                        path_str = first_item.path if hasattr(first_item, "path") else first_item.get("path", "") if isinstance(first_item, dict) else ""
                        if path_str:
                            path = Path(path_str)
                            if path.exists():
                                for parent in path.parents:
                                    if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                                        self._project_root = parent
                                        break
                                if not self._project_root:
                                    self._project_root = path.parent
                                break
        
        self._reload_manual_links()
        
        # Build list of files to analyze
        files_to_analyze: list[Path] = []
        
        # Method 1: Try to get files from hotspots
        hotspots = summary.get("hotspots", {})
        if isinstance(hotspots, dict):
            for category_items in hotspots.values():
                if isinstance(category_items, list):
                    for item in category_items:
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
        
        # Method 2: Try to load from last scan cache
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
            for pattern in ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"]:
                for path in self._project_root.glob(pattern):
                    if path.is_file():
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
            return
        
        # Perform full analysis
        quality_summary = QualitySummary()
        quality_summary.total_files = len(files_to_analyze)
        
        file_reports: list[FileQualityReport] = []
        all_issues: list[QualityIssue] = []
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
            occurrences = cast(list[dict[str, Any]], cluster.get("occurrences", []))
            if len(occurrences) > 1:
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
            occurrences = cast(list[dict[str, Any]], cluster.get("occurrences", []))
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
        
        # Count issues
        quality_summary.total_issues = len(all_issues)
        for issue in all_issues:
            quality_summary.issues_by_severity[issue.severity] = (
                quality_summary.issues_by_severity.get(issue.severity, 0) + 1
            )
            quality_summary.issues_by_category[issue.category] = (
                quality_summary.issues_by_category.get(issue.category, 0) + 1
            )
        
        # Calculate overall score
        score = 100.0
        
        avg_comp = quality_summary.average_complexity
        if avg_comp > self.complexity_threshold:
            score -= min(20, (avg_comp - self.complexity_threshold) * 0.5)
        
        dup_pct = quality_summary.duplication_percentage
        if dup_pct > DUPLICATION_THRESHOLDS["acceptable"]:
            score -= min(15, (dup_pct - DUPLICATION_THRESHOLDS["acceptable"]) * 2)
        
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
        
        self._last_summary = quality_summary
        summary["code_quality"] = quality_summary.to_dict()
        
        logger.info(
            "CodeQualityAnalyzer: analysis complete. Score: %.1f (%s), Issues: %d",
            quality_summary.overall_score,
            quality_summary.overall_grade,
            quality_summary.total_issues
        )

    # Manual links methods
    def _manual_links_path(self) -> Optional[Path]:
        if not self._project_root:
            return None
        if not self._manual_links_file or not str(self._manual_links_file).startswith(str(self._project_root)):
            self._manual_links_file = self._project_root / ".jupiter" / "manual_duplication_links.json"
        return self._manual_links_file

    def _load_manual_links_from_disk(self) -> list[dict[str, Any]]:
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
        return cast(list[dict[str, Any]], links)

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
        links: dict[str, ManualDuplicationLink] = {}
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

    def _apply_manual_links(self, duplications: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not self.manual_links:
            return duplications
        manual_clusters = []
        for link in self.manual_links.values():
            try:
                manual_clusters.append(self._build_manual_cluster(link))
            except Exception as exc:
                logger.error("Failed to build manual duplication cluster '%s': %s", link.link_id, exc)
        return duplications + manual_clusters

    def _build_manual_cluster(self, link: ManualDuplicationLink) -> dict[str, Any]:
        self._manual_file_cache = {}
        occurrences_payload = []
        normalized_blocks = []
        issues: list[str] = []

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

        return {
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

    def _get_file_lines(self, file_path: Path) -> Optional[list[str]]:
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

    def create_manual_link(self, label: Optional[str], cluster_hashes: list[str]) -> dict[str, Any]:
        """Create a manual duplication link from selected clusters."""
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

        location_ranges: dict[tuple[str, str], dict[str, Any]] = {}
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
        
        # Update summary
        if self._last_summary:
            existing = [c for c in self._last_summary.duplication_clusters 
                       if not (c.get("source") == "manual" and c.get("manual_link_id") == link_id)]
            existing.append(cluster)
            self._last_summary.duplication_clusters = existing
        
        return cluster

    def delete_manual_link(self, link_id: str) -> None:
        """Delete a manual duplication link."""
        link = self.manual_links.get(link_id)
        if not link:
            raise ValueError(f"Manual link '{link_id}' not found")
        if link.origin != "file":
            raise ValueError("Only links stored on disk can be removed via API")
        del self.manual_links[link_id]
        self._write_manual_links_to_disk()
        
        # Update summary
        if self._last_summary:
            self._last_summary.duplication_clusters = [
                c for c in self._last_summary.duplication_clusters
                if not (c.get("source") == "manual" and c.get("manual_link_id") == link_id)
            ]

    def recheck_manual_links(self, link_id: Optional[str] = None) -> dict[str, Any]:
        """Re-check manual duplication links."""
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
            # Update summary
            if self._last_summary:
                existing = [c for c in self._last_summary.duplication_clusters 
                           if not (c.get("source") == "manual" and c.get("manual_link_id") == cluster.get("manual_link_id"))]
                existing.append(cluster)
                self._last_summary.duplication_clusters = existing
        return {"status": "ok", "links": refreshed}
