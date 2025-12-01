"""Pylance/Pyright analyzer plugin for Jupiter.

This plugin integrates with Pyright (the engine behind Pylance) to detect
type errors, unused imports, and other static analysis issues during scans.

Requirements:
    pip install pyright

The plugin runs pyright in JSON output mode and parses the results to enrich
Jupiter's scan and analysis reports with type-checking diagnostics.
"""

from __future__ import annotations

import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field, asdict

from jupiter.plugins import PluginUIConfig, PluginUIType

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "0.5.2"


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
    
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PylanceFileReport:
    """Diagnostics for a single file."""
    
    path: str
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    diagnostics: list[PylanceDiagnostic] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
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
    file_reports: list[PylanceFileReport] = field(default_factory=list)
    pyright_version: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "files_with_errors": self.files_with_errors,
            "total_errors": self.total_errors,
            "total_warnings": self.total_warnings,
            "total_info": self.total_info,
            "pyright_version": self.pyright_version,
            "file_reports": [f.to_dict() for f in self.file_reports],
        }


class PylanceAnalyzerPlugin:
    """Plugin that runs Pyright to detect type errors and other issues.
    
    This plugin hooks into Jupiter's scan workflow to provide static type
    analysis for Python files, similar to what Pylance provides in VS Code.
    
    Configuration options:
        enabled: bool - Whether to run analysis (default: True)
        strict: bool - Use strict type checking mode (default: False)
        include_warnings: bool - Include warnings in report (default: True)
        include_info: bool - Include informational messages (default: False)
        max_files: int - Maximum files to analyze (default: 500)
        timeout: int - Timeout in seconds (default: 120)
        extra_args: list[str] - Additional pyright arguments
    """

    name = "pylance_analyzer"
    version = PLUGIN_VERSION
    description = "Static type analysis using Pyright (Pylance engine)."
    trust_level = "stable"
    
    # UI Configuration - this plugin shows in the sidebar
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SIDEBAR,
        menu_icon="🔍",
        menu_label_key="pylance_view",
        menu_order=75,  # After Quality (70), before Plugins (80)
        view_id="pylance",
    )

    def __init__(self) -> None:
        self.enabled = True
        self.strict = False
        self.include_warnings = True
        self.include_info = False
        self.max_files = 500
        self.timeout = 120
        self.extra_args: list[str] = []
        self._last_summary: Optional[PylanceSummary] = None
        self._pyright_available: Optional[bool] = None
        self._pyright_path: Optional[str] = None

    def configure(self, config: dict[str, Any]) -> None:
        """Configure the plugin with the given settings."""
        self.enabled = config.get("enabled", True)
        self.strict = config.get("strict", False)
        self.include_warnings = config.get("include_warnings", True)
        self.include_info = config.get("include_info", False)
        self.max_files = config.get("max_files", 500)
        self.timeout = config.get("timeout", 120)
        self.extra_args = config.get("extra_args", [])
        logger.info(
            "PylanceAnalyzerPlugin configured: enabled=%s strict=%s max_files=%d timeout=%d",
            self.enabled,
            self.strict,
            self.max_files,
            self.timeout,
        )
        logger.debug(
            "PylanceAnalyzerPlugin config include_warnings=%s include_info=%s extra_args=%s",
            self.include_warnings,
            self.include_info,
            self.extra_args,
        )

    def _check_pyright_available(self) -> bool:
        """Check if pyright is installed and available."""
        if self._pyright_available is not None:
            return self._pyright_available

        self._pyright_path = shutil.which("pyright")
        self._pyright_available = self._pyright_path is not None

        if not self._pyright_available:
            logger.warning(
                "Pyright not found. Install with: pip install pyright"
            )
        else:
            logger.debug("Pyright executable found at %s", self._pyright_path)
        return self._pyright_available

    def _run_pyright(self, project_root: Path, python_files: list[str]) -> tuple[Optional[dict[str, Any]], Optional[str]]:
        """Run pyright and return parsed JSON output and error message."""
        if not self._check_pyright_available():
            return None, "Pyright not available"
        
        if not python_files:
            return None, "No files to check"
        
        # Limit files to analyze
        files_to_check = python_files[:self.max_files]
        if len(files_to_check) < len(python_files):
            logger.debug(
                "Truncated python file list from %d to %d entries",
                len(python_files),
                len(files_to_check),
            )
        
        # Build pyright command
        cmd = [self._pyright_path, "--outputjson"]
        
        if self.strict:
            cmd.append("--strict")
        
        cmd.extend(self.extra_args)
        cmd.extend(files_to_check)
        
        logger.info(
            "Running Pyright on %d files (max %d)...",
            len(files_to_check), self.max_files
        )
        logger.debug("Pyright command: %s", cmd)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            logger.debug(
                "Pyright finished with code=%s stdout=%d chars stderr=%d chars",
                result.returncode,
                len(result.stdout or ""),
                len(result.stderr or ""),
            )
            
            # Pyright returns exit code 0 for success, 1 for errors found
            # We need to parse the JSON regardless
            if result.stdout:
                try:
                    parsed = json.loads(result.stdout)
                    logger.debug(
                        "Parsed Pyright JSON with %d diagnostics",
                        len(parsed.get("generalDiagnostics", []) or []),
                    )
                    return parsed, None
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse Pyright output: %s", e)
                    return None, f"JSON parse error: {e}"
            
            if result.returncode not in (0, 1):
                logger.warning(
                    "Pyright exited with code %d: %s",
                    result.returncode, result.stderr
                )
                return None, f"Exit code {result.returncode}: {result.stderr}"
            
            return None, "No output from pyright"
            
        except subprocess.TimeoutExpired:
            logger.error("Pyright timed out after %d seconds", self.timeout)
            return None, "Timeout expired"
        except Exception as e:
            logger.error("Error running Pyright: %s", e)
            return None, str(e)

    def _parse_pyright_output(self, output: dict[str, Any]) -> PylanceSummary:
        """Parse pyright JSON output into our summary format."""
        summary = PylanceSummary()
        summary.pyright_version = output.get("version")
        
        # Group diagnostics by file
        file_diagnostics: dict[str, PylanceFileReport] = {}
        
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
        
        logger.debug(
            "Pyright summary built: files=%d errors=%d warnings=%d infos=%d",
            summary.total_files,
            summary.total_errors,
            summary.total_warnings,
            summary.total_info,
        )
        return summary

    def on_scan(self, report: dict[str, Any]) -> None:
        """Analyze Python files after scan and add diagnostics to report."""
        if not self.enabled:
            logger.debug("PylanceAnalyzerPlugin is disabled, skipping on_scan")
            return
        
        # Extract project root and Python files from report
        root_str = report.get("root")
        if not root_str:
            logger.warning("No project root in report, skipping Pylance analysis.")
            return
        
        project_root = Path(root_str)
        
        # Collect Python files from the scan
        python_files: list[str] = []
        for file_info in report.get("files", []):
            file_path = file_info.get("path", "")
            if file_path.endswith(".py"):
                python_files.append(file_path)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "PylanceAnalyzerPlugin evaluating %d scanned files", len(report.get("files", []))
            )

        if not python_files:
            logger.info("No Python files found, skipping Pylance analysis.")
            report["pylance"] = {"status": "skipped", "reason": "no_python_files"}
            return
        
        logger.info(
            "PylanceAnalyzerPlugin: analyzing %d Python files...",
            len(python_files)
        )
        logger.debug("First python files: %s", python_files[:5])
        
        # Run pyright
        pyright_output, error_msg = self._run_pyright(project_root, python_files)
        
        if pyright_output is None:
            logger.error("Pyright execution failed: %s", error_msg)
            report["pylance"] = {
                "status": "error",
                "reason": "pyright_not_available" if not self._pyright_available else "analysis_failed",
                "message": error_msg
            }
            return
        
        # Parse results
        summary = self._parse_pyright_output(pyright_output)
        self._last_summary = summary
        
        # Add to report
        report["pylance"] = {
            "status": "ok",
            "summary": summary.to_dict(),
        }
        
        logger.info(
            "Pylance analysis complete: %d errors, %d warnings in %d files",
            summary.total_errors,
            summary.total_warnings,
            summary.total_files,
        )
        logger.debug("Pylance summary payload=%s", summary.to_dict())

    def on_analyze(self, summary: dict[str, Any]) -> None:
        """Add Pylance metrics to analysis summary."""
        if not self.enabled:
            logger.debug("PylanceAnalyzerPlugin disabled; skipping on_analyze")
            return
        
        if self._last_summary:
            payload = {
                "total_errors": self._last_summary.total_errors,
                "total_warnings": self._last_summary.total_warnings,
                "files_with_errors": self._last_summary.files_with_errors,
                "pyright_version": self._last_summary.pyright_version,
            }
            summary["pylance"] = payload
            logger.debug("PylanceAnalyzerPlugin appended analysis payload=%s", payload)
            
            # Add to quality metrics if present
            if "quality" in summary and isinstance(summary["quality"], dict):
                summary["quality"]["pylance_errors"] = self._last_summary.total_errors
                summary["quality"]["pylance_warnings"] = self._last_summary.total_warnings

    def get_diagnostics_for_file(self, file_path: str) -> list[PylanceDiagnostic]:
        """Get diagnostics for a specific file from the last analysis."""
        if not self._last_summary:
            logger.debug("No cached Pylance summary; returning empty diagnostics for %s", file_path)
            return []
        
        for file_report in self._last_summary.file_reports:
            if file_report.path == file_path or file_report.path.endswith(file_path):
                logger.debug(
                    "Returning %d diagnostics for %s",
                    len(file_report.diagnostics),
                    file_path,
                )
                return file_report.diagnostics
        
        logger.debug("No diagnostics found for %s", file_path)
        return []

    def get_summary(self) -> Optional[PylanceSummary]:
        """Get the summary from the last analysis."""
        return self._last_summary

    # ─────────────────────────────────────────────────────────────────────────
    # UI Methods - Provide HTML/JS for the Jupiter web interface
    # ─────────────────────────────────────────────────────────────────────────

    def get_ui_html(self) -> str:
        """Return HTML content for the Pylance view."""
        return """
<section class="view-section" id="pylance-section">
    <header class="section-header">
        <div>
            <p class="eyebrow" data-i18n="pylance_eyebrow">Type Analysis</p>
            <h2 data-i18n="pylance_title">Pylance / Pyright Diagnostics</h2>
            <p class="subtitle" data-i18n="pylance_subtitle">Static type checking powered by Pyright, the engine behind VS Code's Pylance extension.</p>
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" id="pylance-refresh-btn" title="Refresh data">
                🔄 <span data-i18n="pylance_refresh">Refresh</span>
            </button>
            <button class="btn btn-secondary" id="pylance-export-btn" title="Export for AI agent">
                📋 <span data-i18n="pylance_export">Export</span>
            </button>
        </div>
    </header>
    
    <!-- Help / Documentation Card -->
    <div class="card help-card" id="pylance-help">
        <details>
            <summary class="help-summary">
                <span class="help-icon">❓</span>
                <span data-i18n="pylance_help_title">What is this page?</span>
            </summary>
            <div class="help-content">
                <p data-i18n="pylance_help_intro">
                    This page displays <strong>static type analysis</strong> results from Pyright, 
                    the same engine that powers the Pylance extension in VS Code.
                </p>
                <h4 data-i18n="pylance_help_what_title">What does it detect?</h4>
                <ul>
                    <li data-i18n="pylance_help_what_1">🔴 <strong>Type errors</strong>: incompatible types, missing attributes, wrong arguments</li>
                    <li data-i18n="pylance_help_what_2">🟡 <strong>Warnings</strong>: unused imports, unreachable code, deprecated usage</li>
                    <li data-i18n="pylance_help_what_3">🔵 <strong>Info</strong>: suggestions for better type annotations</li>
                </ul>
                <h4 data-i18n="pylance_help_how_title">How to use?</h4>
                <ol>
                    <li data-i18n="pylance_help_how_1">Run a <strong>Scan</strong> from the top bar – Pyright analysis runs automatically</li>
                    <li data-i18n="pylance_help_how_2">Review the summary stats and file list below</li>
                    <li data-i18n="pylance_help_how_3">Click <strong>View</strong> on any file to see detailed diagnostics</li>
                    <li data-i18n="pylance_help_how_4">Use <strong>Export</strong> to copy results for AI coding assistants</li>
                </ol>
                <h4 data-i18n="pylance_help_export_title">Export for AI Agents</h4>
                <p data-i18n="pylance_help_export_desc">
                    The <strong>Export</strong> button copies a formatted summary to your clipboard, 
                    ready to paste into ChatGPT, Claude, Copilot, or any AI coding assistant. 
                    The AI can then help you fix the detected issues.
                </p>
                <h4 data-i18n="pylance_help_requirements_title">Requirements</h4>
                <p data-i18n="pylance_help_requirements_desc">
                    Pyright must be installed: <code>pip install pyright</code>
                </p>
            </div>
        </details>
    </div>
    
    <!-- Stats Row -->
    <div class="stats-row" id="pylance-stats">
        <div class="stat-card">
            <span class="stat-value" id="pylance-errors">—</span>
            <span class="stat-label" data-i18n="pylance_errors">Errors</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" id="pylance-warnings">—</span>
            <span class="stat-label" data-i18n="pylance_warnings">Warnings</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" id="pylance-files">—</span>
            <span class="stat-label" data-i18n="pylance_files_affected">Files Affected</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" id="pylance-version">—</span>
            <span class="stat-label" data-i18n="pylance_version">Pyright Version</span>
        </div>
    </div>
    
    <!-- Status Messages -->
    <div class="card warning-card" id="pylance-not-available" style="display: none;">
        <p class="warning-text">
            ⚠️ <span data-i18n="pylance_not_installed">Pyright is not installed.</span>
        </p>
        <p class="muted" data-i18n="pylance_install_hint">Install with: <code>pip install pyright</code></p>
    </div>
    
    <div class="card error-card" id="pylance-error" style="display: none;">
        <p class="error-text">
            ❌ <span data-i18n="pylance_error">Analysis failed.</span>
        </p>
        <p class="muted" id="pylance-error-msg"></p>
    </div>

    <div class="card info-card" id="pylance-no-data" style="display: none;">
        <p>ℹ️ <span data-i18n="pylance_no_data">No Pylance data available.</span></p>
        <p class="muted" data-i18n="pylance_no_data_hint">Run a scan from the top bar to analyze your Python files.</p>
    </div>
    
    <div class="card info-card" id="pylance-no-python" style="display: none;">
        <p>ℹ️ <span data-i18n="pylance_no_python">This project does not contain Python files.</span></p>
        <p class="muted" data-i18n="pylance_no_python_hint">Add .py files or switch to a Python project, then rerun a scan to see diagnostics.</p>
    </div>

    <div class="card success-card" id="pylance-all-good" style="display: none;">
        <p>✅ <span data-i18n="pylance_all_good">No type errors found!</span></p>
        <p class="muted" data-i18n="pylance_all_good_hint">Your Python code passes static type checking.</p>
    </div>
</section>

<!-- Files List Section -->
<section class="view-section" id="pylance-files-section" style="display: none;">
    <p class="eyebrow" data-i18n="pylance_files_eyebrow">By File</p>
    <h3 data-i18n="pylance_files_title">Files with Issues</h3>
    
    <div class="filter-bar">
        <input type="text" id="pylance-filter" class="filter-input" placeholder="Filter by file path..." data-i18n-placeholder="pylance_filter_placeholder">
        <select id="pylance-severity-filter" class="filter-select">
            <option value="all" data-i18n="pylance_filter_all">All</option>
            <option value="error" data-i18n="pylance_filter_errors">Errors only</option>
            <option value="warning" data-i18n="pylance_filter_warnings">Warnings only</option>
        </select>
    </div>
    
    <div class="table-container">
        <table class="data-table" id="pylance-files-table">
            <thead>
                <tr>
                    <th data-i18n="pylance_th_file">File</th>
                    <th data-i18n="pylance_th_errors">Errors</th>
                    <th data-i18n="pylance_th_warnings">Warnings</th>
                    <th data-i18n="pylance_th_actions">Actions</th>
                </tr>
            </thead>
            <tbody id="pylance-files-body">
            </tbody>
        </table>
    </div>
</section>

<!-- File Details Section -->
<section class="view-section" id="pylance-details-section" style="display: none;">
    <p class="eyebrow" data-i18n="pylance_details_eyebrow">Details</p>
    <h3 id="pylance-details-title">Diagnostics</h3>
    
    <div class="details-actions">
        <button class="btn btn-secondary" id="pylance-back-btn" data-i18n="pylance_back">← Back to files</button>
        <button class="btn btn-secondary" id="pylance-export-file-btn">📋 <span data-i18n="pylance_export_file">Export this file</span></button>
    </div>
    
    <div class="table-container">
        <table class="data-table" id="pylance-diagnostics-table">
            <thead>
                <tr>
                    <th data-i18n="pylance_th_line">Line</th>
                    <th data-i18n="pylance_th_severity">Severity</th>
                    <th data-i18n="pylance_th_message">Message</th>
                    <th data-i18n="pylance_th_rule">Rule</th>
                </tr>
            </thead>
            <tbody id="pylance-diagnostics-body">
            </tbody>
        </table>
    </div>
</section>

<!-- Export Modal -->
<div class="modal hidden" id="pylance-export-modal">
    <div class="modal-content" style="max-width: 800px;">
        <header class="modal-header">
            <h3 data-i18n="pylance_export_title">Export Pylance Results</h3>
            <button class="close-btn" data-action="close-pylance-export">&times;</button>
        </header>
        <div class="modal-body">
            <p class="muted" data-i18n="pylance_export_instructions">
                Copy this formatted report and paste it into your AI coding assistant (ChatGPT, Claude, Copilot, etc.)
            </p>
            <textarea id="pylance-export-content" class="export-textarea" readonly rows="20"></textarea>
        </div>
        <footer class="modal-footer">
            <button class="btn btn-primary" id="pylance-copy-btn">📋 <span data-i18n="pylance_copy">Copy to Clipboard</span></button>
            <button class="btn btn-secondary" data-action="close-pylance-export" data-i18n="close">Close</button>
        </footer>
    </div>
</div>
"""

    def get_ui_js(self) -> str:
        """Return JavaScript code for the Pylance view."""
        return """
(function() {
    // Pylance View Controller
    const controller = {
        data: null,
        currentFilePath: null,
        
        getApiBaseUrl() {
            if (typeof state !== 'undefined' && state.apiBaseUrl) {
                return state.apiBaseUrl;
            }
            return window.location.protocol + '//' + window.location.hostname + ':8000';
        },
        
        $(id) {
            return document.getElementById(id);
        },
        
        async init() {
            console.log('[Pylance] Initializing view...');
            await this.loadData();
            this.bindEvents();
            console.log('[Pylance] Initialization complete');
        },
        
        async loadData() {
            console.log('[Pylance] Loading data...');
            try {
                const apiBase = this.getApiBaseUrl();
                const token = localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
                
                console.log('[Pylance] Fetching from:', apiBase + '/reports/last');
                const resp = await fetch(`${apiBase}/reports/last`, {
                    headers: token ? { 'Authorization': 'Bearer ' + token } : {}
                });
                
                console.log('[Pylance] Response status:', resp.status);
                
                if (!resp.ok) {
                    console.log('[Pylance] Response not OK, showing no data');
                    this.showNoData();
                    return;
                }
                
                const report = await resp.json();
                console.log('[Pylance] Report received, pylance data:', report.pylance);
                
                if (!report.pylance) {
                    console.log('[Pylance] No pylance key in report');
                    this.showNoData();
                    return;
                }
                
                if (report.pylance.status === 'error') {
                    if (report.pylance.reason === 'pyright_not_available') {
                        console.log('[Pylance] Pyright not available');
                        this.showNotAvailable();
                    } else {
                        console.log('[Pylance] Error:', report.pylance.reason);
                        this.showError(report.pylance.message || report.pylance.reason);
                    }
                    return;
                }
                
                if (report.pylance.status === 'skipped') {
                    console.log('[Pylance] Analysis was skipped:', report.pylance.reason);
                    if (report.pylance.reason === 'no_python_files') {
                        this.showNoPythonFiles();
                    } else {
                        this.showNoData();
                    }
                    return;
                }
                
                if (report.pylance.status !== 'ok' || !report.pylance.summary) {
                    console.log('[Pylance] Status not ok or no summary');
                    this.showNoData();
                    return;
                }
                
                this.data = report.pylance.summary;
                console.log('[Pylance] Data loaded:', this.data.total_errors, 'errors,', this.data.total_warnings, 'warnings');
                this.render();
                
            } catch (err) {
                console.error('[Pylance] Failed to load data:', err);
                this.showNoData();
            }
        },
        
        showNoData() {
            const noData = this.$('pylance-no-data');
            const notAvail = this.$('pylance-not-available');
            const errorCard = this.$('pylance-error');
            const allGood = this.$('pylance-all-good');
            const noPython = this.$('pylance-no-python');
            const filesSection = this.$('pylance-files-section');
            
            if (noData) noData.style.display = 'block';
            if (notAvail) notAvail.style.display = 'none';
            if (errorCard) errorCard.style.display = 'none';
            if (allGood) allGood.style.display = 'none';
            if (noPython) noPython.style.display = 'none';
            if (filesSection) filesSection.style.display = 'none';
        },
        
        showNotAvailable() {
            const noData = this.$('pylance-no-data');
            const notAvail = this.$('pylance-not-available');
            const errorCard = this.$('pylance-error');
            const allGood = this.$('pylance-all-good');
            const noPython = this.$('pylance-no-python');
            const filesSection = this.$('pylance-files-section');
            
            if (notAvail) notAvail.style.display = 'block';
            if (noData) noData.style.display = 'none';
            if (errorCard) errorCard.style.display = 'none';
            if (allGood) allGood.style.display = 'none';
            if (noPython) noPython.style.display = 'none';
            if (filesSection) filesSection.style.display = 'none';
        },

        showError(msg) {
            const noData = this.$('pylance-no-data');
            const notAvail = this.$('pylance-not-available');
            const errorCard = this.$('pylance-error');
            const errorMsg = this.$('pylance-error-msg');
            const allGood = this.$('pylance-all-good');
            const noPython = this.$('pylance-no-python');
            const filesSection = this.$('pylance-files-section');
            
            if (errorCard) errorCard.style.display = 'block';
            if (errorMsg) errorMsg.textContent = msg;
            
            if (noData) noData.style.display = 'none';
            if (notAvail) notAvail.style.display = 'none';
            if (allGood) allGood.style.display = 'none';
            if (noPython) noPython.style.display = 'none';
            if (filesSection) filesSection.style.display = 'none';
        },
        
        showAllGood() {
            const noData = this.$('pylance-no-data');
            const notAvail = this.$('pylance-not-available');
            const errorCard = this.$('pylance-error');
            const allGood = this.$('pylance-all-good');
            const noPython = this.$('pylance-no-python');
            const filesSection = this.$('pylance-files-section');
            
            if (allGood) allGood.style.display = 'block';
            if (noData) noData.style.display = 'none';
            if (notAvail) notAvail.style.display = 'none';
            if (errorCard) errorCard.style.display = 'none';
            if (noPython) noPython.style.display = 'none';
            if (filesSection) filesSection.style.display = 'none';
        },

        showNoPythonFiles() {
            const noData = this.$('pylance-no-data');
            const notAvail = this.$('pylance-not-available');
            const errorCard = this.$('pylance-error');
            const allGood = this.$('pylance-all-good');
            const noPython = this.$('pylance-no-python');
            const filesSection = this.$('pylance-files-section');

            if (noPython) noPython.style.display = 'block';
            if (noData) noData.style.display = 'none';
            if (notAvail) notAvail.style.display = 'none';
            if (errorCard) errorCard.style.display = 'none';
            if (allGood) allGood.style.display = 'none';
            if (filesSection) filesSection.style.display = 'none';
        },
        
        render() {
            if (!this.data) return;
            
            // Update stats
            const errEl = this.$('pylance-errors');
            const warnEl = this.$('pylance-warnings');
            const filesEl = this.$('pylance-files');
            const verEl = this.$('pylance-version');
            
            if (errEl) errEl.textContent = this.data.total_errors || 0;
            if (warnEl) warnEl.textContent = this.data.total_warnings || 0;
            if (filesEl) filesEl.textContent = this.data.files_with_errors || 0;
            if (verEl) verEl.textContent = this.data.pyright_version || '—';
            
            // Hide all status messages
            const noData = this.$('pylance-no-data');
            const notAvail = this.$('pylance-not-available');
            const errorCard = this.$('pylance-error');
            const allGood = this.$('pylance-all-good');
            const filesSection = this.$('pylance-files-section');
            
            if (noData) noData.style.display = 'none';
            if (notAvail) notAvail.style.display = 'none';
            if (errorCard) errorCard.style.display = 'none';
            
            // Show "all good" or files table
            if (this.data.total_errors === 0 && this.data.total_warnings === 0) {
                if (allGood) allGood.style.display = 'block';
                if (filesSection) filesSection.style.display = 'none';
            } else {
                if (allGood) allGood.style.display = 'none';
                if (filesSection) filesSection.style.display = 'block';
                this.renderFilesTable();
            }
        },
        
        renderFilesTable() {
            const tbody = this.$('pylance-files-body');
            const filterEl = this.$('pylance-filter');
            const severityEl = this.$('pylance-severity-filter');
            
            if (!tbody) return;
            
            const filter = filterEl ? filterEl.value.toLowerCase() : '';
            const severityFilter = severityEl ? severityEl.value : 'all';
            
            tbody.innerHTML = '';
            
            if (!this.data || !this.data.file_reports) return;
            
            const files = this.data.file_reports.filter(f => {
                if (filter && !f.path.toLowerCase().includes(filter)) return false;
                if (severityFilter === 'error' && f.error_count === 0) return false;
                if (severityFilter === 'warning' && f.warning_count === 0) return false;
                return true;
            });
            
            for (const file of files) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td class="path-cell" title="${file.path}">${this.shortenPath(file.path)}</td>
                    <td class="count-cell ${file.error_count > 0 ? 'error-count' : ''}">${file.error_count}</td>
                    <td class="count-cell ${file.warning_count > 0 ? 'warning-count' : ''}">${file.warning_count}</td>
                    <td><button class="btn btn-small" data-path="${file.path}">View</button></td>
                `;
                tbody.appendChild(row);
            }
            
            if (files.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">No files match the filter</td></tr>';
            }
        },
        
        shortenPath(path) {
            const parts = path.replace(/\\\\/g, '/').split('/');
            if (parts.length <= 3) return path;
            return '.../' + parts.slice(-3).join('/');
        },
        
        showFileDetails(path) {
            const file = this.data?.file_reports?.find(f => f.path === path);
            if (!file) return;
            
            this.currentFilePath = path;
            
            const filesSection = this.$('pylance-files-section');
            const detailsSection = this.$('pylance-details-section');
            const detailsTitle = this.$('pylance-details-title');
            const tbody = this.$('pylance-diagnostics-body');
            
            if (filesSection) filesSection.style.display = 'none';
            if (detailsSection) detailsSection.style.display = 'block';
            if (detailsTitle) detailsTitle.textContent = this.shortenPath(path);
            
            if (!tbody) return;
            tbody.innerHTML = '';
            
            for (const diag of file.diagnostics) {
                const row = document.createElement('tr');
                const severityClass = diag.severity === 'error' ? 'severity-error' : 
                                      diag.severity === 'warning' ? 'severity-warning' : 'severity-info';
                row.innerHTML = `
                    <td>${diag.line}:${diag.column}</td>
                    <td class="${severityClass}">${diag.severity}</td>
                    <td class="message-cell">${this.escapeHtml(diag.message)}</td>
                    <td class="rule-cell">${diag.rule || '—'}</td>
                `;
                tbody.appendChild(row);
            }
        },
        
        hideFileDetails() {
            this.currentFilePath = null;
            const detailsSection = this.$('pylance-details-section');
            const filesSection = this.$('pylance-files-section');
            if (detailsSection) detailsSection.style.display = 'none';
            if (filesSection) filesSection.style.display = 'block';
        },
        
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        
        // ─────────────────────────────────────────────────────────────────
        // Export Functions
        // ─────────────────────────────────────────────────────────────────
        
        generateExportText(filePathFilter = null) {
            if (!this.data) return 'No Pylance data available.';
            
            let text = '# Pylance / Pyright Type Analysis Report\\n\\n';
            text += `Generated: ${new Date().toISOString()}\\n`;
            text += `Pyright Version: ${this.data.pyright_version || 'unknown'}\\n\\n`;
            
            text += '## Summary\\n\\n';
            text += `- **Total Errors**: ${this.data.total_errors}\\n`;
            text += `- **Total Warnings**: ${this.data.total_warnings}\\n`;
            text += `- **Files with Issues**: ${this.data.files_with_errors}\\n\\n`;
            
            if (this.data.total_errors === 0 && this.data.total_warnings === 0) {
                text += '✅ No type errors or warnings found!\\n';
                return text;
            }
            
            text += '## Issues by File\\n\\n';
            
            const filesToExport = filePathFilter 
                ? this.data.file_reports.filter(f => f.path === filePathFilter)
                : this.data.file_reports;
            
            for (const file of filesToExport) {
                if (file.error_count === 0 && file.warning_count === 0) continue;
                
                text += `### ${file.path}\\n\\n`;
                text += `Errors: ${file.error_count}, Warnings: ${file.warning_count}\\n\\n`;
                
                for (const diag of file.diagnostics) {
                    const icon = diag.severity === 'error' ? '🔴' : diag.severity === 'warning' ? '🟡' : '🔵';
                    text += `${icon} **Line ${diag.line}:${diag.column}** [${diag.severity}]`;
                    if (diag.rule) text += ` (${diag.rule})`;
                    text += `\\n   ${diag.message}\\n\\n`;
                }
            }
            
            text += '---\\n\\n';
            text += '## Instructions for AI Agent\\n\\n';
            text += 'Please help fix the above type errors and warnings. For each issue:\\n';
            text += '1. Explain what the error means\\n';
            text += '2. Provide the corrected code\\n';
            text += '3. Explain why the fix works\\n';
            
            return text;
        },
        
        showExportModal(filePathFilter = null) {
            const modal = this.$('pylance-export-modal');
            const content = this.$('pylance-export-content');
            
            if (!modal || !content) return;
            
            content.value = this.generateExportText(filePathFilter);
            modal.classList.remove('hidden');
        },
        
        closeExportModal() {
            const modal = this.$('pylance-export-modal');
            if (modal) modal.classList.add('hidden');
        },
        
        async copyToClipboard() {
            const content = this.$('pylance-export-content');
            if (!content) return;
            
            try {
                await navigator.clipboard.writeText(content.value);
                const copyBtn = this.$('pylance-copy-btn');
                if (copyBtn) {
                    const originalText = copyBtn.innerHTML;
                    copyBtn.innerHTML = '✅ Copied!';
                    setTimeout(() => { copyBtn.innerHTML = originalText; }, 2000);
                }
            } catch (err) {
                console.error('[Pylance] Failed to copy:', err);
                content.select();
                document.execCommand('copy');
            }
        },
        
        // ─────────────────────────────────────────────────────────────────
        // Event Bindings
        // ─────────────────────────────────────────────────────────────────
        
        bindEvents() {
            // Refresh button
            this.$('pylance-refresh-btn')?.addEventListener('click', () => this.loadData());
            
            // Export button (all files)
            this.$('pylance-export-btn')?.addEventListener('click', () => this.showExportModal());
            
            // Export current file button
            this.$('pylance-export-file-btn')?.addEventListener('click', () => {
                if (this.currentFilePath) {
                    this.showExportModal(this.currentFilePath);
                }
            });
            
            // Copy button
            this.$('pylance-copy-btn')?.addEventListener('click', () => this.copyToClipboard());
            
            // Close export modal
            document.querySelectorAll('[data-action="close-pylance-export"]').forEach(btn => {
                btn.addEventListener('click', () => this.closeExportModal());
            });
            
            // Filter events
            this.$('pylance-filter')?.addEventListener('input', () => this.renderFilesTable());
            this.$('pylance-severity-filter')?.addEventListener('change', () => this.renderFilesTable());
            
            // View button clicks
            this.$('pylance-files-body')?.addEventListener('click', (e) => {
                if (e.target.matches('button[data-path]')) {
                    this.showFileDetails(e.target.dataset.path);
                }
            });
            
            // Back button
            this.$('pylance-back-btn')?.addEventListener('click', () => this.hideFileDetails());
        }
    };
    
    // Register controller
    window.pylanceView = controller;
    window.pylance_analyzerView = controller;
    console.log('[Pylance] View controller loaded, waiting for init() call...');
})();
"""
