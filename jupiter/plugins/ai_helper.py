"""AI Helper plugin."""

from __future__ import annotations

import logging
from typing import Any, List, Dict, Optional
from dataclasses import dataclass, asdict

PLUGIN_VERSION = "0.3.1"

logger = logging.getLogger(__name__)

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
    version = PLUGIN_VERSION
    description = "AI-assisted analysis and suggestions."

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {}
        self.enabled = False
        self.provider = "mock"
        self.api_key = None
        self.scanned_files: List[Dict[str, Any]] = []

    def configure(self, settings: Dict[str, Any]) -> None:
        """Configure the plugin."""
        self.config = settings or {}
        self.enabled = self.config.get("enabled", True)  # Default to True if settings exist
        self.provider = self.config.get("provider", "mock")
        self.api_key = self.config.get("api_key")
        logger.info(
            "AIHelperPlugin configured: enabled=%s, provider=%s",
            self.enabled,
            self.provider,
        )
        logger.debug(
            "AIHelperPlugin config keys=%s api_key_present=%s",
            sorted(self.config.keys()),
            bool(self.api_key),
        )

    def on_scan(self, report: dict[str, Any]) -> None:
        """Hook called after a scan is complete."""
        files = report.get("files", [])
        self.scanned_files = files
        logger.info("AIHelperPlugin captured %d files from scan", len(files))
        if logger.isEnabledFor(logging.DEBUG):
            sample = [f.get("path") for f in files[:5]]
            logger.debug("AIHelperPlugin sample files=%s", sample)

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """
        Hook called after analysis. 
        Populates summary['refactoring'] with AI suggestions.
        """
        if not self.enabled:
            logger.debug("AIHelperPlugin disabled; skipping on_analyze")
            return

        suggestions = self._generate_suggestions(summary)
        logger.info("AIHelperPlugin generated %d suggestion(s)", len(suggestions))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "AIHelperPlugin suggestions detail=%s",
                [asdict(s) for s in suggestions],
            )
        
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
        logger.debug("AIHelperPlugin generating suggestions via provider=%s", self.provider)
        suggestions = []
        
        # Mock implementation for demonstration
        if self.provider == "mock":
            # Example: Suggest docstrings for files with many functions but low size (heuristic)
            if "python_summary" in summary and summary["python_summary"]:
                py_sum = summary["python_summary"]
                if py_sum.get("avg_functions_per_file", 0) > 3:
                    suggestion = AISuggestion(
                        path="Global",
                        type="doc",
                        details="High function density detected. Consider adding module-level docstrings.",
                        severity="info"
                    )
                    suggestions.append(suggestion)
                    logger.debug("AIHelperPlugin added doc suggestion: %s", asdict(suggestion))
                
                if py_sum.get("total_potentially_unused_functions", 0) > 10:
                    suggestion = AISuggestion(
                        path="Global",
                        type="cleanup",
                        details=f"Found {py_sum['total_potentially_unused_functions']} potentially unused functions. Run 'jupiter check' to verify.",
                        severity="low"
                    )
                    suggestions.append(suggestion)
                    logger.debug("AIHelperPlugin added cleanup suggestion: %s", asdict(suggestion))
            
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
                                suggestion = AISuggestion(
                                    path=item["path"],
                                    type="refactoring",
                                    details=f"File is large ({size // 1024}KB). AI suggests splitting into smaller modules.",
                                    severity="medium"
                                )
                                suggestions.append(suggestion)
                                logger.debug("AIHelperPlugin added large-file suggestion: %s", asdict(suggestion))
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
                                suggestion = AISuggestion(
                                    path=item["path"],
                                    type="refactoring",
                                    details=f"High function count ({count}). This might be a 'God Object'. Consider extracting logic.",
                                    severity="high"
                                )
                                suggestions.append(suggestion)
                                logger.debug("AIHelperPlugin added god-object suggestion: %s", asdict(suggestion))
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
                    suggestion = AISuggestion(
                        path="Global",
                        type="testing",
                        details=f"Detected {missing_tests} source files without obvious corresponding tests.",
                        severity="medium"
                    )
                    suggestions.append(suggestion)
                    logger.debug("AIHelperPlugin added testing suggestion: %s", asdict(suggestion))

        return suggestions
