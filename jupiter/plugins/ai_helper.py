"""AI Helper plugin."""

from __future__ import annotations

from typing import Any, List, Dict, Optional
from dataclasses import dataclass, asdict
from jupiter import __version__

@dataclass
class AISuggestion:
    path: str
    type: str  # refactoring, doc, security, optimization
    details: str
    severity: str  # info, warning, critical
    code_snippet: Optional[str] = None

class AIHelperPlugin:
    """
    AI-assisted analysis plugin.
    
    This plugin provides an interface for AI-based code analysis.
    It hooks into the analysis phase to provide suggestions.
    """

    name = "ai_helper"
    version = __version__
    description = "AI-assisted analysis and suggestions."

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.enabled = False
        self.provider = "mock"
        self.api_key = None
        self.scanned_files: List[Dict[str, Any]] = []

    def configure(self, settings: Dict[str, Any]) -> None:
        """Configure the plugin."""
        self.config = settings
        self.enabled = settings.get("enabled", True) # Default to True if settings exist
        self.provider = settings.get("provider", "mock")
        self.api_key = settings.get("api_key", None)

    def on_scan(self, report: dict[str, Any]) -> None:
        """Hook called after a scan is complete."""
        if "files" in report:
            self.scanned_files = report["files"]

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """
        Hook called after analysis. 
        Populates summary['refactoring'] with AI suggestions.
        """
        if not self.enabled:
            return

        suggestions = self._generate_suggestions(summary)
        
        # Merge into existing refactoring list or create it
        if "refactoring" not in summary:
            summary["refactoring"] = []
        
        # Convert dataclasses to dicts matching RefactoringRecommendation model
        for s in suggestions:
            summary["refactoring"].append({
                "path": s.path,
                "type": s.type,
                "details": f"[AI] {s.details}",
                "severity": s.severity
            })

    def _generate_suggestions(self, summary: dict[str, Any]) -> List[AISuggestion]:
        """
        Generate suggestions based on the summary.
        In a real implementation, this would call an LLM.
        """
        suggestions = []
        
        # Mock implementation for demonstration
        if self.provider == "mock":
            # Example: Suggest docstrings for files with many functions but low size (heuristic)
            if "python_summary" in summary and summary["python_summary"]:
                py_sum = summary["python_summary"]
                if py_sum.get("avg_functions_per_file", 0) > 3:
                    suggestions.append(AISuggestion(
                        path="Global",
                        type="doc",
                        details="High function density detected. Consider adding module-level docstrings.",
                        severity="info"
                    ))
                
                if py_sum.get("total_potentially_unused_functions", 0) > 10:
                     suggestions.append(AISuggestion(
                        path="Global",
                        type="cleanup",
                        details=f"Found {py_sum['total_potentially_unused_functions']} potentially unused functions. Run 'jupiter check' to verify.",
                        severity="low"
                    ))
            
            # Example: Suggest splitting large files
            if "hotspots" in summary:
                # Check largest files
                if "largest_files" in summary["hotspots"]:
                    for item in summary["hotspots"]["largest_files"]:
                        # details format is "12345 bytes"
                        try:
                            size_str = item.get("details", "0").split()[0]
                            size = int(size_str)
                            if size > 50 * 1024: # 50KB
                                suggestions.append(AISuggestion(
                                    path=item["path"],
                                    type="refactoring",
                                    details=f"File is large ({size // 1024}KB). AI suggests splitting into smaller modules.",
                                    severity="medium"
                                ))
                        except (ValueError, IndexError):
                            pass

                # Check complex files (God Object candidate)
                if "most_functions" in summary["hotspots"]:
                    for item in summary["hotspots"]["most_functions"]:
                        # details format is "N functions"
                        try:
                            count_str = item.get("details", "0").split()[0]
                            count = int(count_str)
                            if count > 20:
                                suggestions.append(AISuggestion(
                                    path=item["path"],
                                    type="refactoring",
                                    details=f"High function count ({count}). This might be a 'God Object'. Consider extracting logic.",
                                    severity="high"
                                ))
                        except (ValueError, IndexError):
                            pass

            # Test Gap Analysis
            # Check if we have source files without corresponding tests
            if self.scanned_files:
                test_files = {f["path"] for f in self.scanned_files if "test" in f["path"] or "tests" in f["path"]}
                source_files = [f for f in self.scanned_files if f["file_type"] == "py" and "test" not in f["path"]]
                
                missing_tests = 0
                for src in source_files:
                    # Simple heuristic: check if a file with "test_" + name exists
                    # This is very basic and assumes flat structure or matching names
                    # A better check would be to see if the file name appears in any test file name
                    src_name = src["path"].split("\\")[-1].split("/")[-1] # Handle both separators
                    has_test = any(src_name in t for t in test_files)
                    if not has_test:
                        missing_tests += 1
                
                if missing_tests > 0:
                     suggestions.append(AISuggestion(
                        path="Global",
                        type="testing",
                        details=f"Detected {missing_tests} source files without obvious corresponding tests.",
                        severity="medium"
                    ))

        return suggestions
