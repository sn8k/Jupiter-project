"""
Pylance Analyzer - Core Analysis Logic

This module contains the core Pyright/Pylance analysis logic, isolated from
the plugin lifecycle management.

@version 1.0.0
"""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import logging


@dataclass
class PylanceDiagnostic:
    """A single diagnostic from Pyright/Pylance."""
    
    file: str
    line: int
    column: int
    end_line: int
    end_column: int
    severity: str  # "error", "warning", "information"
    message: str
    rule: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PylanceFileReport:
    """Diagnostics for a single file."""
    
    path: str
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    diagnostics: List[PylanceDiagnostic] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass
class PylanceSummary:
    """Summary of Pylance analysis across all files."""
    
    total_files: int = 0
    files_with_errors: int = 0
    total_errors: int = 0
    total_warnings: int = 0
    total_info: int = 0
    file_reports: List[PylanceFileReport] = field(default_factory=list)
    pyright_version: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_files": self.total_files,
            "files_with_errors": self.files_with_errors,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_info": self.total_info,
            "pyright_version": self.pyright_version,
            "file_reports": [f.to_dict() for f in self.file_reports],
        }


class PylanceAnalyzer:
    """
    Core Pyright analysis engine.
    
    This class handles the actual interaction with Pyright and parsing
    of results, isolated from the plugin lifecycle.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        strict: bool = False,
        include_warnings: bool = True,
        include_info: bool = False,
        max_files: int = 500,
        timeout: int = 120,
        extra_args: Optional[List[str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.enabled = enabled
        self.strict = strict
        self.include_warnings = include_warnings
        self.include_info = include_info
        self.max_files = max_files
        self.timeout = timeout
        self.extra_args = extra_args or []
        self._logger = logger or logging.getLogger(__name__)
        
        self._pyright_available: Optional[bool] = None
        self._pyright_path: Optional[str] = None
        self._last_summary: Optional[PylanceSummary] = None
        self._last_error: Optional[str] = None
    
    @property
    def pyright_path(self) -> Optional[str]:
        """Get the path to pyright executable."""
        return self._pyright_path
    
    @property
    def last_summary(self) -> Optional[PylanceSummary]:
        """Get the summary from the last analysis."""
        return self._last_summary
    
    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error
    
    def configure(
        self,
        enabled: bool = True,
        strict: bool = False,
        include_warnings: bool = True,
        include_info: bool = False,
        max_files: int = 500,
        timeout: int = 120,
        extra_args: Optional[List[str]] = None,
    ) -> None:
        """Update analyzer configuration."""
        self.enabled = enabled
        self.strict = strict
        self.include_warnings = include_warnings
        self.include_info = include_info
        self.max_files = max_files
        self.timeout = timeout
        if extra_args is not None:
            self.extra_args = extra_args
    
    def reset_config(self) -> None:
        """Reset to default configuration."""
        self.enabled = True
        self.strict = False
        self.include_warnings = True
        self.include_info = False
        self.max_files = 500
        self.timeout = 120
        self.extra_args = []
    
    def check_pyright_available(self) -> bool:
        """Check if pyright is installed and available."""
        if self._pyright_available is not None:
            return self._pyright_available
        
        self._pyright_path = shutil.which("pyright")
        self._pyright_available = self._pyright_path is not None
        
        if not self._pyright_available:
            self._logger.warning(
                "Pyright not found. Install with: pip install pyright"
            )
        else:
            self._logger.debug("Pyright executable found at %s", self._pyright_path)
        
        return self._pyright_available
    
    def analyze_report(self, report: Dict[str, Any]) -> Optional[PylanceSummary]:
        """
        Analyze Python files from a scan report.
        
        Args:
            report: The scan report containing files to analyze.
            
        Returns:
            PylanceSummary if analysis succeeded, None otherwise.
        """
        self._last_error = None
        
        if not self.enabled:
            self._logger.debug("Analyzer disabled, skipping")
            self._last_error = "disabled"
            return None
        
        # Extract project root
        root_str = report.get("root")
        if not root_str:
            self._logger.warning("No project root in report")
            self._last_error = "no_project_root"
            return None
        
        project_root = Path(root_str)
        
        # Collect Python files
        python_files: List[str] = []
        for file_info in report.get("files", []):
            file_path = file_info.get("path", "")
            if file_path.endswith(".py"):
                python_files.append(file_path)
        
        if not python_files:
            self._logger.info("No Python files found")
            self._last_error = "no_python_files"
            return None
        
        self._logger.info("Analyzing %d Python files...", len(python_files))
        
        # Run analysis
        return self.analyze_files(project_root, python_files)
    
    def analyze_files(
        self,
        project_root: Path,
        python_files: List[str],
    ) -> Optional[PylanceSummary]:
        """
        Run Pyright analysis on a list of files.
        
        Args:
            project_root: Root directory of the project.
            python_files: List of Python file paths to analyze.
            
        Returns:
            PylanceSummary if analysis succeeded, None otherwise.
        """
        pyright_output, error_msg = self._run_pyright(project_root, python_files)
        
        if pyright_output is None:
            self._logger.error("Pyright execution failed: %s", error_msg)
            self._last_error = error_msg
            return None
        
        # Parse results
        summary = self._parse_pyright_output(pyright_output)
        self._last_summary = summary
        
        self._logger.info(
            "Analysis complete: %d errors, %d warnings in %d files",
            summary.total_errors,
            summary.total_warnings,
            summary.total_files,
        )
        
        return summary
    
    def get_diagnostics_for_file(self, file_path: str) -> List[PylanceDiagnostic]:
        """Get diagnostics for a specific file from the last analysis."""
        if not self._last_summary:
            return []
        
        for file_report in self._last_summary.file_reports:
            if file_report.path == file_path or file_report.path.endswith(file_path):
                return file_report.diagnostics
        
        return []
    
    def _run_pyright(
        self,
        project_root: Path,
        python_files: List[str],
    ) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Run pyright and return parsed JSON output and error message."""
        if not self.check_pyright_available():
            return None, "Pyright not available"
        
        if not python_files:
            return None, "No files to check"
        
        # Limit files to analyze
        files_to_check = python_files[:self.max_files]
        if len(files_to_check) < len(python_files):
            self._logger.debug(
                "Truncated file list from %d to %d entries",
                len(python_files),
                len(files_to_check),
            )
        
        # Build pyright command
        cmd = [self._pyright_path, "--outputjson"]
        
        if self.strict:
            cmd.append("--strict")
        
        cmd.extend(self.extra_args)
        cmd.extend(files_to_check)
        
        self._logger.debug("Running: %s", " ".join(cmd[:5]) + "...")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            # Pyright returns exit code 0 for success, 1 for errors found
            if result.stdout:
                try:
                    parsed = json.loads(result.stdout)
                    return parsed, None
                except json.JSONDecodeError as e:
                    return None, f"JSON parse error: {e}"
            
            if result.returncode not in (0, 1):
                return None, f"Exit code {result.returncode}: {result.stderr}"
            
            return None, "No output from pyright"
            
        except subprocess.TimeoutExpired:
            return None, f"Timeout after {self.timeout}s"
        except Exception as e:
            return None, str(e)
    
    def _parse_pyright_output(self, output: Dict[str, Any]) -> PylanceSummary:
        """Parse pyright JSON output into our summary format."""
        summary = PylanceSummary()
        summary.pyright_version = output.get("version")
        
        # Group diagnostics by file
        file_diagnostics: Dict[str, PylanceFileReport] = {}
        
        diagnostics = output.get("generalDiagnostics", [])
        
        for diag in diagnostics:
            file_path = diag.get("file", "")
            severity = diag.get("severity", "error").lower()
            
            # Filter based on configuration
            if severity == "information" and not self.include_info:
                continue
            if severity == "warning" and not self.include_warnings:
                continue
            
            # Get or create file report
            if file_path not in file_diagnostics:
                file_diagnostics[file_path] = PylanceFileReport(path=file_path)
            
            file_report = file_diagnostics[file_path]
            
            # Extract range info
            range_info = diag.get("range", {})
            start = range_info.get("start", {})
            end = range_info.get("end", {})
            
            diagnostic = PylanceDiagnostic(
                file=file_path,
                line=start.get("line", 0) + 1,  # Pyright uses 0-indexed lines
                column=start.get("character", 0) + 1,
                end_line=end.get("line", 0) + 1,
                end_column=end.get("character", 0) + 1,
                severity=severity,
                message=diag.get("message", ""),
                rule=diag.get("rule"),
            )
            
            file_report.diagnostics.append(diagnostic)
            
            # Update counts
            if severity == "error":
                file_report.error_count += 1
                summary.total_errors += 1
            elif severity == "warning":
                file_report.warning_count += 1
                summary.total_warnings += 1
            else:
                file_report.info_count += 1
                summary.total_info += 1
        
        # Finalize summary
        summary.file_reports = list(file_diagnostics.values())
        summary.total_files = len(file_diagnostics)
        summary.files_with_errors = sum(
            1 for f in summary.file_reports if f.error_count > 0
        )
        
        return summary
