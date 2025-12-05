"""
Code Quality Plugin - Data Classes
==================================

Data classes for quality analysis results.

Version: 0.8.1
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


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
    issues: list[QualityIssue] = field(default_factory=list)
    
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
    issues_by_severity: dict[str, int] = field(default_factory=dict)
    issues_by_category: dict[str, int] = field(default_factory=dict)
    file_reports: list[FileQualityReport] = field(default_factory=list)
    duplication_clusters: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    
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
    occurrences: list[ManualLinkOccurrence] = field(default_factory=list)
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
