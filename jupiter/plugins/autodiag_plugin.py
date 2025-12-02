"""Autodiag plugin for Jupiter.

This plugin provides a web interface for Jupiter's autodiagnostic capabilities,
allowing users to:
- Run autodiag analysis from the UI
- View false positive detection results
- Explore function usage confidence scores
- Get actionable recommendations

The plugin integrates with the existing autodiag infrastructure in jupiter/core/autodiag.py
and the autodiag API endpoints in jupiter/server/routers/autodiag.py.

Version: 1.1.0
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from jupiter.plugins import PluginUIConfig, PluginUIType

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "1.1.0"


@dataclass
class AutodiagPluginState:
    """Current state of the autodiag plugin."""
    
    last_run_timestamp: Optional[float] = None
    last_status: str = "idle"  # idle, running, success, partial, failed
    false_positive_count: int = 0
    true_unused_count: int = 0
    false_positive_rate: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AutodiagPlugin:
    """Plugin that provides autodiag UI and integration.
    
    This plugin hooks into Jupiter's scan/analyze workflow to provide
    automated self-diagnostic capabilities with false positive detection.
    
    Configuration options:
        enabled: bool - Whether the plugin is active (default: True)
        auto_run_on_scan: bool - Run autodiag after each scan (default: False)
        show_confidence_scores: bool - Display confidence scores (default: True)
        diag_port: int - Port for autodiag API (default: 8081)
    """

    name = "autodiag"
    version = PLUGIN_VERSION
    description = "Self-diagnostic analysis with false positive detection for unused functions."
    trust_level = "stable"
    
    # UI Configuration - this plugin shows in both sidebar AND settings
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.BOTH,
        menu_icon="🔬",
        menu_label_key="autodiag_view",
        menu_order=65,  # After CI (60), before Quality (70)
        view_id="autodiag",
        settings_section="autodiag",
    )

    def __init__(self) -> None:
        self.enabled = True
        self.auto_run_on_scan = False
        self.show_confidence_scores = True
        self.diag_port = 8081
        self._state = AutodiagPluginState()
        self._last_report: Optional[Dict[str, Any]] = None

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin with the given settings."""
        self.enabled = config.get("enabled", True)
        self.auto_run_on_scan = config.get("auto_run_on_scan", False)
        self.show_confidence_scores = config.get("show_confidence_scores", True)
        self.diag_port = config.get("diag_port", 8081)
        
        logger.info(
            "AutodiagPlugin configured: enabled=%s auto_run=%s diag_port=%d",
            self.enabled,
            self.auto_run_on_scan,
            self.diag_port,
        )

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Hook called after a scan is completed."""
        if not self.enabled:
            logger.debug("AutodiagPlugin is disabled, skipping on_scan")
            return
        
        # Add autodiag section to report
        if "plugins_data" not in report:
            report["plugins_data"] = {}
        
        report["plugins_data"][self.name] = {
            "status": "available",
            "message": "Autodiag available. Run from the Autodiag panel.",
            "diag_endpoint": f"http://127.0.0.1:{self.diag_port}/diag",
        }
        
        logger.debug("AutodiagPlugin added status to scan report")

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Hook called after an analysis is completed."""
        if not self.enabled:
            logger.debug("AutodiagPlugin is disabled, skipping on_analyze")
            return
        
        # Extract function usage info if available
        python_summary = summary.get("python_summary", {})
        usage_summary = python_summary.get("usage_summary", {})
        
        if usage_summary:
            # Add autodiag-relevant metrics
            if "plugins_data" not in summary:
                summary["plugins_data"] = {}
            
            summary["plugins_data"][self.name] = {
                "function_metrics": {
                    "total": usage_summary.get("total", 0),
                    "used": usage_summary.get("used", 0),
                    "likely_used": usage_summary.get("likely_used", 0),
                    "possibly_unused": usage_summary.get("possibly_unused", 0),
                    "unused": usage_summary.get("unused", 0),
                },
                "last_state": self._state.to_dict(),
            }
            
            logger.debug("AutodiagPlugin enriched analysis summary with function metrics")

    # ─────────────────────────────────────────────────────────────────────────
    # Plugin API Methods
    # These methods are part of the plugin public interface and may be called
    # dynamically via getattr() by the PluginManager or external integrations.
    # Static analysis may incorrectly flag them as unused.
    # ─────────────────────────────────────────────────────────────────────────

    def get_state(self) -> AutodiagPluginState:
        """Get the current plugin state.
        
        This is a public API method that can be called by:
        - PluginManager for state inspection
        - External integrations querying plugin status
        - Future UI components displaying plugin state
        """
        return self._state

    def get_last_report(self) -> Optional[Dict[str, Any]]:
        """Get the last autodiag report.
        
        This is a public API method for external access to autodiag results.
        Can be called by UI components or integrations needing the latest report.
        """
        return self._last_report

    def update_from_report(self, report: Dict[str, Any]) -> None:
        """Update internal state from an autodiag report.
        
        Called when a new autodiag report is generated, to keep plugin state in sync.
        This is part of the plugin lifecycle and may be invoked by the autodiag runner.
        """
        self._last_report = report
        
        fp_detection = report.get("false_positive_detection", {})
        self._state.false_positive_count = fp_detection.get("false_positive_count", 0)
        self._state.true_unused_count = fp_detection.get("true_unused_count", 0)
        self._state.false_positive_rate = fp_detection.get("false_positive_rate", 0.0)
        self._state.last_status = report.get("status", "unknown")
        self._state.last_run_timestamp = report.get("timestamp")
        self._state.recommendations = report.get("recommendations", [])
        
        logger.info(
            "AutodiagPlugin state updated: fp_rate=%.1f%% status=%s",
            self._state.false_positive_rate,
            self._state.last_status,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # UI Methods - Provide HTML/JS for the Jupiter web interface
    # ─────────────────────────────────────────────────────────────────────────

    def get_ui_html(self) -> str:
        """Return HTML content for the Autodiag view."""
        return '''
<!-- Main Layout: Two columns - Content left, Info right -->
<div class="autodiag-layout">
    <!-- LEFT COLUMN: Main Content -->
    <div class="autodiag-main">
        <!-- Header with actions -->
        <header class="autodiag-header">
            <div class="autodiag-header-left">
                <p class="eyebrow" data-i18n="autodiag_eyebrow">Self-Diagnostic</p>
                <h2 data-i18n="autodiag_title">Autodiag Analysis</h2>
            </div>
            <div class="autodiag-header-actions">
                <button class="btn btn-primary btn-lg" id="autodiag-run-btn" title="Run autodiag">
                    🚀 <span data-i18n="autodiag_run">Run Autodiag</span>
                </button>
                <button class="btn btn-secondary" id="autodiag-export-btn" title="Export for AI agent">
                    📋 <span data-i18n="autodiag_export">Export</span>
                </button>
                <button class="btn btn-secondary" id="autodiag-refresh-btn" title="Refresh">
                    🔄
                </button>
            </div>
        </header>
        
        <!-- Status Messages -->
        <div class="autodiag-status-area">
            <div class="card info-card" id="autodiag-idle">
                <div class="status-icon">💤</div>
                <div class="status-content">
                    <p data-i18n="autodiag_idle">No autodiag analysis has been run yet.</p>
                    <p class="muted" data-i18n="autodiag_idle_hint">Click "Run Autodiag" to start the analysis.</p>
                </div>
            </div>
            
            <div class="card warning-card" id="autodiag-running" style="display: none;">
                <div class="status-icon spinning">⏳</div>
                <div class="status-content">
                    <p data-i18n="autodiag_running">Autodiag is running...</p>
                    <p class="muted" data-i18n="autodiag_running_hint">Testing CLI, API, and plugin scenarios.</p>
                    <div class="progress-container">
                        <div class="progress-bar" id="autodiag-progress"></div>
                    </div>
                </div>
            </div>
            
            <div class="card error-card" id="autodiag-error" style="display: none;">
                <div class="status-icon">❌</div>
                <div class="status-content">
                    <p data-i18n="autodiag_error">Autodiag failed.</p>
                    <p class="muted" id="autodiag-error-msg"></p>
                </div>
            </div>
            
            <div class="card error-card" id="autodiag-server-error" style="display: none;">
                <div class="status-icon">⚠️</div>
                <div class="status-content">
                    <p data-i18n="autodiag_server_error">Autodiag server not available.</p>
                    <p class="muted" data-i18n="autodiag_server_hint">Server runs on port 8081 (localhost). Check your config.</p>
                </div>
            </div>
        </div>
        
        <!-- Stats Dashboard -->
        <div class="autodiag-dashboard" id="autodiag-stats" style="display: none;">
            <div class="stat-card stat-large stat-success">
                <div class="stat-icon">✅</div>
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-fp-count">0</span>
                    <span class="stat-label" data-i18n="autodiag_false_positives">False Positives</span>
                </div>
            </div>
            <div class="stat-card stat-large stat-warning">
                <div class="stat-icon">⚠️</div>
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-unused-count">0</span>
                    <span class="stat-label" data-i18n="autodiag_truly_unused">Truly Unused</span>
                </div>
            </div>
            <div class="stat-card stat-large">
                <div class="stat-icon">📊</div>
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-accuracy-rate">0%</span>
                    <span class="stat-label" data-i18n="autodiag_accuracy_rate">Accuracy</span>
                </div>
            </div>
            <div class="stat-card stat-medium">
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-scenarios">0</span>
                    <span class="stat-label" data-i18n="autodiag_scenarios">Scenarios</span>
                </div>
            </div>
            <div class="stat-card stat-medium">
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-duration">0s</span>
                    <span class="stat-label" data-i18n="autodiag_duration">Duration</span>
                </div>
            </div>
        </div>
        
        <!-- Tabs Navigation -->
        <div class="autodiag-tabs" id="autodiag-tabs" style="display: none;">
            <button class="tab-btn active" data-tab="scenarios">
                🧪 <span data-i18n="autodiag_tab_scenarios">Scenarios</span>
                <span class="tab-badge" id="autodiag-tab-scenarios-count">0</span>
            </button>
            <button class="tab-btn" data-tab="false-positives">
                ✅ <span data-i18n="autodiag_tab_fp">False Positives</span>
                <span class="tab-badge" id="autodiag-tab-fp-count">0</span>
            </button>
            <button class="tab-btn" data-tab="unused">
                ⚠️ <span data-i18n="autodiag_tab_unused">Unused</span>
                <span class="tab-badge" id="autodiag-tab-unused-count">0</span>
            </button>
            <button class="tab-btn" data-tab="confidence">
                📈 <span data-i18n="autodiag_tab_confidence">Confidence</span>
            </button>
            <button class="tab-btn" data-tab="recommendations">
                💡 <span data-i18n="autodiag_tab_recommendations">Tips</span>
            </button>
        </div>
        
        <!-- Tab Content: Scenarios -->
        <div class="tab-content" id="tab-scenarios" style="display: none;">
            <div class="tab-header">
                <h3 data-i18n="autodiag_scenarios_title">Executed Scenarios</h3>
            </div>
            <div class="table-container">
                <table class="data-table" id="autodiag-scenarios-table">
                    <thead>
                        <tr>
                            <th data-i18n="autodiag_th_scenario">Scenario</th>
                            <th data-i18n="autodiag_th_status">Status</th>
                            <th data-i18n="autodiag_th_duration">Duration</th>
                            <th data-i18n="autodiag_th_error">Error</th>
                            <th data-i18n="autodiag_th_triggered">Functions Triggered</th>
                        </tr>
                    </thead>
                    <tbody id="autodiag-scenarios-body"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Tab Content: False Positives -->
        <div class="tab-content" id="tab-false-positives" style="display: none;">
            <div class="tab-header">
                <h3 data-i18n="autodiag_fp_title">False Positives Detected</h3>
                <div class="filter-inline">
                    <input type="text" id="autodiag-fp-filter" class="filter-input" placeholder="Filter..." data-i18n-placeholder="autodiag_filter_placeholder">
                </div>
            </div>
            <div class="table-container">
                <table class="data-table" id="autodiag-fp-table">
                    <thead>
                        <tr>
                            <th data-i18n="autodiag_th_function">Function</th>
                            <th data-i18n="autodiag_th_file">File</th>
                            <th data-i18n="autodiag_th_reason">Reason</th>
                            <th data-i18n="autodiag_th_scenario">Triggered By</th>
                        </tr>
                    </thead>
                    <tbody id="autodiag-fp-body"></tbody>
                </table>
            </div>
            <div class="empty-state" id="autodiag-fp-empty" style="display: none;">
                <span class="empty-icon">🎉</span>
                <p data-i18n="autodiag_no_fp">No false positives detected!</p>
            </div>
        </div>
        
        <!-- Tab Content: Unused -->
        <div class="tab-content" id="tab-unused" style="display: none;">
            <div class="tab-header">
                <h3 data-i18n="autodiag_unused_title">Truly Unused Functions</h3>
            </div>
            <div class="unused-grid" id="autodiag-unused-list"></div>
            <div class="empty-state" id="autodiag-unused-empty" style="display: none;">
                <span class="empty-icon">✨</span>
                <p data-i18n="autodiag_no_unused">All functions are being used!</p>
            </div>
        </div>
        
        <!-- Tab Content: Confidence -->
        <div class="tab-content" id="tab-confidence" style="display: none;">
            <div class="tab-header">
                <h3 data-i18n="autodiag_conf_title">Function Usage Confidence</h3>
                <div class="filter-inline">
                    <input type="text" id="autodiag-conf-filter" class="filter-input" placeholder="Filter..." data-i18n-placeholder="autodiag_filter_placeholder">
                    <select id="autodiag-conf-status-filter" class="filter-select">
                        <option value="all" data-i18n="autodiag_filter_all">All</option>
                        <option value="unused">Unused</option>
                        <option value="possibly_unused">Possibly</option>
                        <option value="likely_used">Likely</option>
                        <option value="used">Used</option>
                    </select>
                    <button class="btn btn-secondary btn-sm" id="autodiag-load-confidence-btn">
                        📊 <span data-i18n="autodiag_load_confidence">Load Data</span>
                    </button>
                </div>
            </div>
            <div class="table-container">
                <table class="data-table" id="autodiag-confidence-table">
                    <thead>
                        <tr>
                            <th data-i18n="autodiag_th_function">Function</th>
                            <th data-i18n="autodiag_th_file">File</th>
                            <th data-i18n="autodiag_th_status">Status</th>
                            <th data-i18n="autodiag_th_confidence">Confidence</th>
                            <th data-i18n="autodiag_th_reasons">Reasons</th>
                        </tr>
                    </thead>
                    <tbody id="autodiag-confidence-body"></tbody>
                </table>
            </div>
        </div>
        
        <!-- Tab Content: Recommendations -->
        <div class="tab-content" id="tab-recommendations" style="display: none;">
            <div class="tab-header">
                <h3 data-i18n="autodiag_rec_title">Recommendations</h3>
            </div>
            <div class="recommendations-list" id="autodiag-recommendations"></div>
            <div class="empty-state" id="autodiag-rec-empty" style="display: none;">
                <span class="empty-icon">👍</span>
                <p data-i18n="autodiag_no_rec">No recommendations - everything looks good!</p>
            </div>
        </div>
    </div>
    
    <!-- RIGHT COLUMN: Sidebar with Help & Settings -->
    <aside class="autodiag-sidebar" id="autodiag-sidebar">
        <!-- Quick Settings Panel -->
        <div class="sidebar-panel">
            <div class="panel-header">
                <span class="panel-icon">⚙️</span>
                <h4 data-i18n="autodiag_quick_settings">Quick Settings</h4>
            </div>
            <div class="panel-content">
                <div class="setting-row">
                    <label class="toggle-label">
                        <input type="checkbox" id="autodiag-opt-skip-cli">
                        <span data-i18n="autodiag_opt_skip_cli">Skip CLI tests</span>
                    </label>
                </div>
                <div class="setting-row">
                    <label class="toggle-label">
                        <input type="checkbox" id="autodiag-opt-skip-api">
                        <span data-i18n="autodiag_opt_skip_api">Skip API tests</span>
                    </label>
                </div>
                <div class="setting-row">
                    <label class="toggle-label">
                        <input type="checkbox" id="autodiag-opt-skip-plugins">
                        <span data-i18n="autodiag_opt_skip_plugins">Skip plugin tests</span>
                    </label>
                </div>
                <div class="setting-row">
                    <label class="input-label" data-i18n="autodiag_opt_timeout">Timeout (s):</label>
                    <input type="number" id="autodiag-opt-timeout" value="30" min="5" max="120" class="setting-input-sm">
                </div>
            </div>
        </div>
        
        <!-- Help Panel -->
        <div class="sidebar-panel">
            <div class="panel-header">
                <span class="panel-icon">❓</span>
                <h4 data-i18n="autodiag_help_title">What is Autodiag?</h4>
            </div>
            <div class="panel-content">
                <p class="help-text" data-i18n="autodiag_help_intro">
                    Autodiag validates static analysis by running dynamic tests to detect false positives.
                </p>
                
                <div class="help-steps">
                    <div class="help-step">
                        <span class="step-icon">1️⃣</span>
                        <span data-i18n="autodiag_help_step_1_short">Static Analysis</span>
                    </div>
                    <div class="help-step">
                        <span class="step-icon">2️⃣</span>
                        <span data-i18n="autodiag_help_step_2_short">Dynamic Tests</span>
                    </div>
                    <div class="help-step">
                        <span class="step-icon">3️⃣</span>
                        <span data-i18n="autodiag_help_step_3_short">Compare Results</span>
                    </div>
                    <div class="help-step">
                        <span class="step-icon">4️⃣</span>
                        <span data-i18n="autodiag_help_step_4_short">Generate Report</span>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Confidence Legend -->
        <div class="sidebar-panel">
            <div class="panel-header">
                <span class="panel-icon">📊</span>
                <h4 data-i18n="autodiag_legend_title">Confidence Legend</h4>
            </div>
            <div class="panel-content">
                <div class="legend-item">
                    <span class="legend-badge badge-used">USED</span>
                    <span class="legend-desc" data-i18n="autodiag_legend_used">Called directly</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge badge-likely">LIKELY</span>
                    <span class="legend-desc" data-i18n="autodiag_legend_likely">Decorated/registered</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge badge-possibly">POSSIBLY</span>
                    <span class="legend-desc" data-i18n="autodiag_legend_possibly">Uncertain usage</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge badge-unused">UNUSED</span>
                    <span class="legend-desc" data-i18n="autodiag_legend_unused">No usage found</span>
                </div>
            </div>
        </div>
        
        <!-- Server Status -->
        <div class="sidebar-panel">
            <div class="panel-header">
                <span class="panel-icon">🖥️</span>
                <h4 data-i18n="autodiag_server_title">Server Status</h4>
            </div>
            <div class="panel-content">
                <div class="server-status" id="autodiag-server-status">
                    <span class="status-dot" id="autodiag-status-dot"></span>
                    <span id="autodiag-status-text" data-i18n="autodiag_checking">Checking...</span>
                </div>
                <p class="server-url">
                    <code id="autodiag-server-url">http://127.0.0.1:8081</code>
                </p>
            </div>
        </div>
    </aside>
</div>

<!-- Export Modal -->
<div class="modal hidden" id="autodiag-export-modal">
    <div class="modal-content" style="max-width: 800px;">
        <header class="modal-header">
            <h3 data-i18n="autodiag_export_title">Export Autodiag Results</h3>
            <button class="close-btn" id="autodiag-export-close">&times;</button>
        </header>
        <div class="modal-body">
            <p class="muted" data-i18n="autodiag_export_instructions">
                Copy this formatted report and paste it into your AI coding assistant (ChatGPT, Claude, Copilot, etc.)
            </p>
            <textarea id="autodiag-export-content" class="export-textarea" readonly rows="20"></textarea>
        </div>
        <footer class="modal-footer">
            <button class="btn btn-primary" id="autodiag-copy-btn">📋 <span data-i18n="autodiag_copy">Copy to Clipboard</span></button>
            <button class="btn btn-secondary" id="autodiag-export-close-btn" data-i18n="close">Close</button>
        </footer>
    </div>
</div>
'''

    def get_ui_js(self) -> str:
        """Return JavaScript code for the Autodiag view."""
        return '''
(function() {
    "use strict";
    
    // Configuration
    let DIAG_PORT = parseInt(localStorage.getItem("autodiag_port") || "8081");
    let DIAG_BASE_URL = `http://127.0.0.1:${DIAG_PORT}`;
    
    // State
    let currentReport = null;
    let confidenceData = null;
    let currentTab = "scenarios";
    
    // Get auth headers from global state (if available)
    function getAuthHeaders() {
        const headers = { "Content-Type": "application/json" };
        // Access global state.token (defined in app.js)
        if (typeof state !== "undefined" && state.token) {
            headers["Authorization"] = `Bearer ${state.token}`;
        }
        return headers;
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Initialization
    // ─────────────────────────────────────────────────────────────────────
    
    function init() {
        console.log("[AutodiagPlugin] Initializing...");
        
        // Bind main actions
        bindClick("autodiag-run-btn", runAutodiag);
        bindClick("autodiag-refresh-btn", refreshData);
        bindClick("autodiag-load-confidence-btn", loadConfidenceData);
        // Toggle sidebar removed
        
        // Bind export actions
        bindClick("autodiag-export-btn", showExportModal);
        bindClick("autodiag-copy-btn", copyToClipboard);
        bindClick("autodiag-export-close", closeExportModal);
        bindClick("autodiag-export-close-btn", closeExportModal);
        
        // Bind filters
        bindInput("autodiag-fp-filter", filterFalsePositives);
        bindInput("autodiag-conf-filter", filterConfidence);
        bindChange("autodiag-conf-status-filter", filterConfidence);
        
        // Bind tabs
        document.querySelectorAll(".autodiag-tabs .tab-btn").forEach(btn => {
            btn.addEventListener("click", () => switchTab(btn.dataset.tab));
        });
        
        // Load saved options
        loadOptions();
        
        // Check server health
        checkDiagServerHealth();
        
        console.log("[AutodiagPlugin] Initialized");
    }
    
    function bindClick(id, fn) {
        const el = document.getElementById(id);
        if (el) el.addEventListener("click", fn);
    }
    
    function bindInput(id, fn) {
        const el = document.getElementById(id);
        if (el) el.addEventListener("input", fn);
    }
    
    function bindChange(id, fn) {
        const el = document.getElementById(id);
        if (el) el.addEventListener("change", fn);
    }
    
    function loadOptions() {
        const skipCli = document.getElementById("autodiag-opt-skip-cli");
        const skipApi = document.getElementById("autodiag-opt-skip-api");
        const skipPlugins = document.getElementById("autodiag-opt-skip-plugins");
        const timeout = document.getElementById("autodiag-opt-timeout");
        
        if (skipCli) skipCli.checked = localStorage.getItem("autodiag_skip_cli") === "true";
        if (skipApi) skipApi.checked = localStorage.getItem("autodiag_skip_api") === "true";
        if (skipPlugins) skipPlugins.checked = localStorage.getItem("autodiag_skip_plugins") === "true";
        if (timeout) timeout.value = localStorage.getItem("autodiag_timeout") || "30";
        
        // Save on change
        [skipCli, skipApi, skipPlugins].forEach(el => {
            if (el) el.addEventListener("change", saveOptions);
        });
        if (timeout) timeout.addEventListener("change", saveOptions);
    }
    
    function saveOptions() {
        const skipCli = document.getElementById("autodiag-opt-skip-cli")?.checked;
        const skipApi = document.getElementById("autodiag-opt-skip-api")?.checked;
        const skipPlugins = document.getElementById("autodiag-opt-skip-plugins")?.checked;
        const timeout = document.getElementById("autodiag-opt-timeout")?.value;
        
        localStorage.setItem("autodiag_skip_cli", skipCli);
        localStorage.setItem("autodiag_skip_api", skipApi);
        localStorage.setItem("autodiag_skip_plugins", skipPlugins);
        localStorage.setItem("autodiag_timeout", timeout);
    }
    
    function getOptions() {
        return {
            skip_cli: document.getElementById("autodiag-opt-skip-cli")?.checked || false,
            skip_api: document.getElementById("autodiag-opt-skip-api")?.checked || false,
            skip_plugins: document.getElementById("autodiag-opt-skip-plugins")?.checked || false,
            timeout: parseInt(document.getElementById("autodiag-opt-timeout")?.value || "30"),
        };
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Tab Navigation
    // ─────────────────────────────────────────────────────────────────────
    
    function switchTab(tabName) {
        currentTab = tabName;
        
        // Update tab buttons
        document.querySelectorAll(".autodiag-tabs .tab-btn").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.tab === tabName);
        });
        
        // Update tab content
        document.querySelectorAll(".tab-content").forEach(content => {
            content.style.display = "none";
        });
        
        const activeContent = document.getElementById(`tab-${tabName}`);
        if (activeContent) activeContent.style.display = "block";
    }
    
    // Sidebar is always visible, toggle removed
    function toggleSidebar_DISABLED() {
        const sidebar = document.getElementById("autodiag-sidebar");
        if (sidebar) {
            sidebar.classList.toggle("collapsed");
        }
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // API Calls
    // ─────────────────────────────────────────────────────────────────────
    
    async function checkDiagServerHealth() {
        const statusDot = document.getElementById("autodiag-status-dot");
        const statusText = document.getElementById("autodiag-status-text");
        const serverUrl = document.getElementById("autodiag-server-url");
        
        if (serverUrl) serverUrl.textContent = DIAG_BASE_URL;
        
        try {
            const resp = await fetch(`${DIAG_BASE_URL}/diag/health`, { 
                method: "GET",
                mode: "cors",
                headers: getAuthHeaders(),
            });
            if (resp.ok) {
                console.log("[AutodiagPlugin] Diag server is healthy");
                if (statusDot) statusDot.className = "status-dot online";
                if (statusText) statusText.textContent = t("autodiag_server_online") || "Online";
                hideElement("autodiag-server-error");
            } else {
                throw new Error("Not OK");
            }
        } catch (e) {
            console.warn("[AutodiagPlugin] Diag server not reachable:", e.message);
            if (statusDot) statusDot.className = "status-dot offline";
            if (statusText) statusText.textContent = t("autodiag_server_offline") || "Offline";
            showElement("autodiag-server-error");
        }
    }
    
    async function runAutodiag() {
        console.log("[AutodiagPlugin] Running autodiag...");
        
        // Get options
        const opts = getOptions();
        const params = new URLSearchParams();
        if (opts.skip_cli) params.append("skip_cli", "true");
        if (opts.skip_api) params.append("skip_api", "true");
        if (opts.skip_plugins) params.append("skip_plugins", "true");
        if (opts.timeout) params.append("timeout", opts.timeout.toString());
        
        // Update UI state
        hideElement("autodiag-idle");
        hideElement("autodiag-error");
        hideElement("autodiag-stats");
        hideElement("autodiag-tabs");
        hideAllTabs();
        showElement("autodiag-running");
        
        // Animate progress bar
        const progressBar = document.getElementById("autodiag-progress");
        if (progressBar) {
            progressBar.style.width = "0%";
            animateProgress(progressBar, 0, 90, 8000);
        }
        
        try {
            const url = `${DIAG_BASE_URL}/diag/run?${params.toString()}`;
            const resp = await fetch(url, {
                method: "POST",
                headers: getAuthHeaders(),
                mode: "cors",
            });
            
            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
            }
            
            const report = await resp.json();
            console.log("[AutodiagPlugin] Autodiag complete:", report);
            
            // Complete progress
            if (progressBar) progressBar.style.width = "100%";
            
            // Store and render
            currentReport = report;
            setTimeout(() => renderReport(report), 300);
            
        } catch (e) {
            console.error("[AutodiagPlugin] Autodiag failed:", e);
            hideElement("autodiag-running");
            showElement("autodiag-error");
            setText("autodiag-error-msg", e.message);
        }
    }
    
    async function refreshData() {
        console.log("[AutodiagPlugin] Refreshing data...");
        await checkDiagServerHealth();
    }
    
    async function loadConfidenceData() {
        console.log("[AutodiagPlugin] Loading confidence data...");
        
        try {
            const resp = await fetch(`${DIAG_BASE_URL}/diag/functions`, { 
                mode: "cors",
                headers: getAuthHeaders(),
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            
            confidenceData = await resp.json();
            console.log("[AutodiagPlugin] Confidence data loaded:", confidenceData);
            
            renderConfidenceTable(confidenceData.functions || []);
            
        } catch (e) {
            console.error("[AutodiagPlugin] Failed to load confidence data:", e);
            alert(t("autodiag_confidence_error") || "Failed to load data. Is server running?");
        }
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Rendering
    // ─────────────────────────────────────────────────────────────────────
    
    function hideAllTabs() {
        document.querySelectorAll(".tab-content").forEach(el => el.style.display = "none");
    }
    
    function renderReport(report) {
        hideElement("autodiag-running");
        hideElement("autodiag-idle");
        
        const status = report.status || "unknown";
        
        if (status === "failed") {
            showElement("autodiag-error");
            setText("autodiag-error-msg", report.recommendations?.[0] || "Unknown error");
            return;
        }
        
        // Show dashboard
        showElement("autodiag-stats");
        showElement("autodiag-tabs");
        
        const fpDetection = report.false_positive_detection || {};
        const dynamicValidation = report.dynamic_validation || {};
        const scenarios = report.scenario_results || [];
        const fps = report.false_positives || [];
        const unused = report.true_unused || [];
        const recommendations = report.recommendations || [];
        
        // Update stats
        setText("autodiag-fp-count", fpDetection.false_positive_count || 0);
        setText("autodiag-unused-count", fpDetection.true_unused_count || 0);
        
        // Use accuracy_rate (higher is better) instead of fp_rate (confusing)
        const accuracyRate = fpDetection.accuracy_rate || report.accuracy_rate || 100;
        setText("autodiag-accuracy-rate", accuracyRate.toFixed(1) + "%");
        
        setText("autodiag-scenarios", dynamicValidation.scenarios_run || 0);
        setText("autodiag-duration", (report.duration_seconds || 0).toFixed(1) + "s");
        
        // Update tab badges
        setText("autodiag-tab-scenarios-count", scenarios.length);
        setText("autodiag-tab-fp-count", fps.length);
        setText("autodiag-tab-unused-count", unused.length);
        
        // Color accuracy rate (higher = better)
        const accuracyEl = document.getElementById("autodiag-accuracy-rate");
        if (accuracyEl) {
            accuracyEl.className = accuracyRate >= 95 ? "stat-value stat-success" : 
                                   accuracyRate >= 80 ? "stat-value stat-warning" : "stat-value stat-error";
        }
        
        // Render all sections
        renderScenarioResults(scenarios);
        renderFalsePositives(fps);
        renderTrulyUnused(unused);
        renderRecommendations(recommendations);
        
        // Show first tab with content
        if (scenarios.length > 0) {
            switchTab("scenarios");
        } else if (fps.length > 0) {
            switchTab("false-positives");
        } else if (unused.length > 0) {
            switchTab("unused");
        } else {
            switchTab("recommendations");
        }
    }
    
    function renderScenarioResults(scenarios) {
        const tbody = document.getElementById("autodiag-scenarios-body");
        if (!tbody) return;
        
        // Debug: log raw scenario data
        console.log("[AutodiagPlugin] Scenarios data:", JSON.stringify(scenarios, null, 2));
        
        if (scenarios.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">${t("autodiag_no_scenarios") || "No scenarios run"}</td></tr>`;
            return;
        }
        
        tbody.innerHTML = scenarios.map(s => {
            // Debug: log each scenario's error_message field
            console.log("[AutodiagPlugin] Scenario:", s.name, "status:", s.status, "error_message:", s.error_message);
            
            const statusClass = s.status === "passed" ? "status-success" : 
                               s.status === "failed" ? "status-error" : "status-warning";
            const statusIcon = s.status === "passed" ? "✅" : 
                              s.status === "failed" ? "❌" : "⏭️";
            
            // Build error message display - check multiple sources
            let errorMsg = s.error_message || "";
            if (!errorMsg && s.status === "failed") {
                // Fallback: build from details
                if (s.details?.exit_code !== undefined && s.details.exit_code !== 0) {
                    errorMsg = `Exit code ${s.details.exit_code}`;
                } else if (s.details?.status_code !== undefined && s.details.status_code >= 400) {
                    errorMsg = `HTTP ${s.details.status_code}`;
                }
            }
            const errorCell = errorMsg 
                ? `<span class="error-text" title="${escapeHtml(errorMsg)}">${truncateText(errorMsg, 50)}</span>`
                : "—";
            
            return `
                <tr class="${s.status === 'failed' ? 'row-error' : ''}">
                    <td><code>${escapeHtml(s.name)}</code></td>
                    <td class="${statusClass}">${statusIcon} ${s.status}</td>
                    <td>${s.duration_seconds?.toFixed(2) || 0}s</td>
                    <td class="error-cell">${errorCell}</td>
                    <td class="wrap-cell">${s.triggered_functions?.join(", ") || "—"}</td>
                </tr>
            `;
        }).join("");
    }
    
    function renderFalsePositives(fps) {
        const tbody = document.getElementById("autodiag-fp-body");
        const emptyState = document.getElementById("autodiag-fp-empty");
        
        if (!tbody) return;
        
        if (fps.length === 0) {
            tbody.innerHTML = "";
            if (emptyState) emptyState.style.display = "flex";
            return;
        }
        
        if (emptyState) emptyState.style.display = "none";
        
        tbody.innerHTML = fps.map(fp => `
            <tr>
                <td><code>${escapeHtml(fp.function_name)}</code></td>
                <td class="path-cell" title="${escapeHtml(fp.file_path)}">${truncatePath(fp.file_path, 30)}</td>
                <td>${escapeHtml(fp.reason)}</td>
                <td><code>${escapeHtml(fp.scenario)}</code></td>
            </tr>
        `).join("");
    }
    
    function renderTrulyUnused(unused) {
        const list = document.getElementById("autodiag-unused-list");
        const emptyState = document.getElementById("autodiag-unused-empty");
        
        if (!list) return;
        
        if (unused.length === 0) {
            list.innerHTML = "";
            if (emptyState) emptyState.style.display = "flex";
            return;
        }
        
        if (emptyState) emptyState.style.display = "none";
        
        list.innerHTML = unused.map(fn => {
            const parts = fn.split("::");
            const name = parts[parts.length - 1] || fn;
            const file = parts.length > 1 ? parts[0] : "";
            return `
                <div class="unused-item">
                    <code class="unused-name">${escapeHtml(name)}</code>
                    <span class="unused-file" title="${escapeHtml(file)}">${truncatePath(file, 25)}</span>
                </div>
            `;
        }).join("");
    }
    
    function renderRecommendations(recommendations) {
        const container = document.getElementById("autodiag-recommendations");
        const emptyState = document.getElementById("autodiag-rec-empty");
        
        if (!container) return;
        
        if (recommendations.length === 0) {
            container.innerHTML = "";
            if (emptyState) emptyState.style.display = "flex";
            return;
        }
        
        if (emptyState) emptyState.style.display = "none";
        
        container.innerHTML = recommendations.map((rec, i) => `
            <div class="recommendation-card">
                <span class="rec-number">${i + 1}</span>
                <span class="rec-text">${escapeHtml(rec)}</span>
            </div>
        `).join("");
    }
    
    function renderConfidenceTable(functions) {
        const tbody = document.getElementById("autodiag-confidence-body");
        if (!tbody) return;
        
        if (functions.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="empty-cell">${t("autodiag_no_data") || "No data. Click 'Load Data'."}</td></tr>`;
            return;
        }
        
        tbody.innerHTML = functions.map(fn => {
            const confidence = ((fn.confidence || 0) * 100).toFixed(0);
            const statusClass = getStatusClass(fn.status);
            const confClass = getConfidenceClass(fn.confidence);
            
            return `
                <tr>
                    <td><code>${escapeHtml(fn.name)}</code></td>
                    <td class="path-cell" title="${escapeHtml(fn.file_path || "")}">${truncatePath(fn.file_path || "", 25)}</td>
                    <td><span class="status-badge ${statusClass}">${fn.status}</span></td>
                    <td><span class="confidence-badge ${confClass}">${confidence}%</span></td>
                    <td class="reasons-cell">${(fn.reasons || []).slice(0, 2).join(", ") || "—"}</td>
                </tr>
            `;
        }).join("");
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Filtering
    // ─────────────────────────────────────────────────────────────────────
    
    function filterFalsePositives() {
        const filter = document.getElementById("autodiag-fp-filter")?.value?.toLowerCase() || "";
        const rows = document.querySelectorAll("#autodiag-fp-body tr");
        
        rows.forEach(row => {
            const text = row.textContent?.toLowerCase() || "";
            row.style.display = text.includes(filter) ? "" : "none";
        });
    }
    
    function filterConfidence() {
        const textFilter = document.getElementById("autodiag-conf-filter")?.value?.toLowerCase() || "";
        const statusFilter = document.getElementById("autodiag-conf-status-filter")?.value || "all";
        const rows = document.querySelectorAll("#autodiag-confidence-body tr");
        
        rows.forEach(row => {
            const text = row.textContent?.toLowerCase() || "";
            const status = row.querySelector(".status-badge")?.textContent?.toLowerCase() || "";
            
            const matchesText = text.includes(textFilter);
            const matchesStatus = statusFilter === "all" || status.includes(statusFilter.replace("_", " "));
            
            row.style.display = (matchesText && matchesStatus) ? "" : "none";
        });
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────────────────────
    
    function showElement(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = "block";
    }
    
    function hideElement(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
    }
    
    function setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }
    
    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
    
    function truncatePath(path, maxLen = 40) {
        if (!path || path.length <= maxLen) return path || "";
        return "..." + path.slice(-maxLen);
    }
    
    function truncateText(text, maxLen = 50) {
        if (!text || text.length <= maxLen) return text || "";
        return text.slice(0, maxLen) + "...";
    }
    
    function getStatusClass(status) {
        switch (status?.toLowerCase()) {
            case "used": return "badge-used";
            case "likely_used": return "badge-likely";
            case "possibly_unused": return "badge-possibly";
            case "unused": return "badge-unused";
            default: return "";
        }
    }
    
    function getConfidenceClass(confidence) {
        if (confidence >= 0.8) return "conf-high";
        if (confidence >= 0.5) return "conf-medium";
        return "conf-low";
    }
    
    function animateProgress(el, from, to, duration) {
        const start = performance.now();
        const diff = to - from;
        
        function step(timestamp) {
            const elapsed = timestamp - start;
            const progress = Math.min(elapsed / duration, 1);
            el.style.width = (from + diff * progress) + "%";
            if (progress < 1) requestAnimationFrame(step);
        }
        
        requestAnimationFrame(step);
    }
    
    function t(key) {
        if (typeof window.t === "function") return window.t(key);
        return key;
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Export Functions
    // ─────────────────────────────────────────────────────────────────────
    
    function generateExportText() {
        if (!currentReport) {
            return "# Autodiag Report\\n\\nNo autodiag analysis has been run yet. Click 'Run Autodiag' first.";
        }
        
        let text = "# Jupiter Autodiag Report\\n\\n";
        text += `Generated: ${new Date().toISOString()}\\n`;
        text += `Status: ${currentReport.status || "unknown"}\\n`;
        text += `Duration: ${(currentReport.duration_seconds || 0).toFixed(2)}s\\n\\n`;
        
        // Summary
        const fpDetection = currentReport.false_positive_detection || {};
        text += "## Summary\\n\\n";
        text += `- **False Positives Detected**: ${fpDetection.false_positive_count || 0}\\n`;
        text += `- **Truly Unused Functions**: ${fpDetection.true_unused_count || 0}\\n`;
        text += `- **False Positive Rate**: ${(fpDetection.false_positive_rate || 0).toFixed(1)}%\\n`;
        text += `- **Scenarios Run**: ${currentReport.dynamic_validation?.scenarios_run || 0}\\n\\n`;
        
        // Scenario Results
        const scenarios = currentReport.scenario_results || [];
        if (scenarios.length > 0) {
            text += "## Scenario Results\\n\\n";
            text += "| Scenario | Status | Duration | Triggered Functions |\\n";
            text += "|----------|--------|----------|---------------------|\\n";
            for (const s of scenarios) {
                const status = s.status === "passed" ? "✅ Passed" : s.status === "failed" ? "❌ Failed" : "⏭️ Skipped";
                const triggered = (s.triggered_functions || []).slice(0, 3).join(", ") || "—";
                text += `| ${s.name} | ${status} | ${(s.duration_seconds || 0).toFixed(2)}s | ${triggered} |\\n`;
            }
            text += "\\n";
        }
        
        // False Positives
        const falsePositives = currentReport.false_positives || [];
        if (falsePositives.length > 0) {
            text += "## False Positives Detected\\n\\n";
            text += "These functions were incorrectly marked as unused by static analysis:\\n\\n";
            for (const fp of falsePositives) {
                text += "### \\`" + fp.function_name + "\\`\\n";
                text += "- **File**: \\`" + fp.file_path + "\\`\\n";
                text += "- **Reason**: " + fp.reason + "\\n";
                text += "- **Detected by scenario**: \\`" + fp.scenario + "\\`\\n\\n";
            }
        }
        
        // Truly Unused
        const trulyUnused = currentReport.true_unused || [];
        if (trulyUnused.length > 0) {
            text += "## Truly Unused Functions\\n\\n";
            text += "These functions appear to be genuinely unused and can potentially be removed:\\n\\n";
            for (const fn of trulyUnused) {
                text += "- \\`" + fn + "\\`\\n";
            }
            text += "\\n";
        }
        
        // Recommendations
        const recommendations = currentReport.recommendations || [];
        if (recommendations.length > 0) {
            text += "## Recommendations\\n\\n";
            for (let i = 0; i < recommendations.length; i++) {
                text += `${i + 1}. ${recommendations[i]}\\n`;
            }
            text += "\\n";
        }
        
        // Instructions for AI
        text += "---\\n\\n";
        text += "## Instructions for AI Agent\\n\\n";
        text += "Based on this autodiag report, please help with the following:\\n\\n";
        
        if (trulyUnused.length > 0) {
            text += "### Cleanup Task\\n";
            text += "Review the truly unused functions listed above. For each one:\\n";
            text += "1. Confirm if it can be safely removed\\n";
            text += "2. Check for any dynamic usage patterns that might have been missed\\n";
            text += "3. If safe, provide the code to remove the function\\n\\n";
        }
        
        if (falsePositives.length > 0) {
            text += "### Analysis Improvement\\n";
            text += "The false positives detected indicate patterns the static analyzer missed. Please:\\n";
            text += "1. Explain why each false positive was not detected statically\\n";
            text += "2. Suggest improvements to the static analysis heuristics\\n\\n";
        }
        
        if (recommendations.length > 0) {
            text += "### Follow-up Actions\\n";
            text += "Please help implement the recommendations listed above.\\n";
        }
        
        return text;
    }
    
    function showExportModal() {
        const modal = document.getElementById("autodiag-export-modal");
        const content = document.getElementById("autodiag-export-content");
        
        if (!modal || !content) return;
        
        content.value = generateExportText();
        modal.classList.remove("hidden");
    }
    
    function closeExportModal() {
        const modal = document.getElementById("autodiag-export-modal");
        if (modal) modal.classList.add("hidden");
    }
    
    async function copyToClipboard() {
        const content = document.getElementById("autodiag-export-content");
        if (!content) return;
        
        try {
            await navigator.clipboard.writeText(content.value);
            const copyBtn = document.getElementById("autodiag-copy-btn");
            if (copyBtn) {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = "✅ Copied!";
                setTimeout(() => { copyBtn.innerHTML = originalText; }, 2000);
            }
        } catch (err) {
            console.error("[AutodiagPlugin] Failed to copy:", err);
            content.select();
            document.execCommand("copy");
        }
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Initialize
    // ─────────────────────────────────────────────────────────────────────
    
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
    
    window.AutodiagPlugin = { init, runAutodiag, refreshData, loadConfidenceData, showExportModal, getCurrentReport: () => currentReport };
})();
'''

    def get_settings_html(self) -> str:
        """Return HTML for the settings section."""
        return '''
<div class="settings-group autodiag-settings-container" id="autodiag-settings">
    <div class="settings-header">
        <h4 data-i18n="autodiag_settings_title">🔬 Autodiag Settings</h4>
        <p class="settings-description" data-i18n="autodiag_settings_description">
            Configure the automatic diagnostic tool for false-positive detection.
        </p>
    </div>
    
    <div class="settings-section">
        <h5 data-i18n="autodiag_settings_general">General</h5>
        
        <div class="setting-item toggle-setting">
            <div class="setting-content">
                <label for="autodiag-enabled" class="setting-label">
                    <span data-i18n="autodiag_setting_enabled">Enable autodiag plugin</span>
                </label>
                <p class="setting-hint" data-i18n="autodiag_setting_enabled_hint">
                    When disabled, the autodiag view will be hidden from the sidebar.
                </p>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="autodiag-enabled" checked>
                <span class="toggle-slider"></span>
            </label>
        </div>
        
        <div class="setting-item toggle-setting">
            <div class="setting-content">
                <label for="autodiag-auto-run" class="setting-label">
                    <span data-i18n="autodiag_setting_auto_run">Auto-run after each scan</span>
                </label>
                <p class="setting-hint" data-i18n="autodiag_setting_auto_run_hint">
                    ⚠️ Warning: This can slow down scans significantly.
                </p>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="autodiag-auto-run">
                <span class="toggle-slider"></span>
            </label>
        </div>
    </div>
    
    <div class="settings-section">
        <h5 data-i18n="autodiag_settings_display">Display</h5>
        
        <div class="setting-item toggle-setting">
            <div class="setting-content">
                <label for="autodiag-show-confidence" class="setting-label">
                    <span data-i18n="autodiag_setting_confidence">Show confidence scores</span>
                </label>
                <p class="setting-hint" data-i18n="autodiag_setting_confidence_hint">
                    Display confidence percentages in the function analysis table.
                </p>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="autodiag-show-confidence" checked>
                <span class="toggle-slider"></span>
            </label>
        </div>
    </div>
    
    <div class="settings-section">
        <h5 data-i18n="autodiag_settings_server">Server Configuration</h5>
        
        <div class="setting-item">
            <div class="setting-content">
                <label for="autodiag-port" class="setting-label" data-i18n="autodiag_setting_port">Autodiag server port</label>
                <p class="setting-hint" data-i18n="autodiag_setting_port_hint">
                    Port number for the local autodiag server (default: 8081).
                </p>
            </div>
            <input type="number" id="autodiag-port" value="8081" min="1024" max="65535" class="setting-input number-input">
        </div>
        
        <div class="setting-item">
            <div class="setting-content">
                <label for="autodiag-timeout" class="setting-label" data-i18n="autodiag_setting_timeout">Timeout (seconds)</label>
                <p class="setting-hint" data-i18n="autodiag_setting_timeout_hint">
                    Maximum execution time for each scenario.
                </p>
            </div>
            <input type="number" id="autodiag-settings-timeout" value="30" min="5" max="300" class="setting-input number-input">
        </div>
    </div>
    
    <div class="settings-section">
        <h5 data-i18n="autodiag_settings_scenarios">Scenario Options</h5>
        
        <div class="setting-item toggle-setting">
            <div class="setting-content">
                <label for="autodiag-skip-cli" class="setting-label">
                    <span data-i18n="autodiag_setting_skip_cli">Skip CLI scenarios</span>
                </label>
                <p class="setting-hint" data-i18n="autodiag_setting_skip_cli_hint">
                    Disable command-line interface testing scenarios.
                </p>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="autodiag-skip-cli">
                <span class="toggle-slider"></span>
            </label>
        </div>
        
        <div class="setting-item toggle-setting">
            <div class="setting-content">
                <label for="autodiag-skip-api" class="setting-label">
                    <span data-i18n="autodiag_setting_skip_api">Skip API scenarios</span>
                </label>
                <p class="setting-hint" data-i18n="autodiag_setting_skip_api_hint">
                    Disable HTTP API testing scenarios.
                </p>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="autodiag-skip-api">
                <span class="toggle-slider"></span>
            </label>
        </div>
        
        <div class="setting-item toggle-setting">
            <div class="setting-content">
                <label for="autodiag-skip-plugins" class="setting-label">
                    <span data-i18n="autodiag_setting_skip_plugins">Skip plugin scenarios</span>
                </label>
                <p class="setting-hint" data-i18n="autodiag_setting_skip_plugins_hint">
                    Disable plugin-related testing scenarios.
                </p>
            </div>
            <label class="toggle-switch">
                <input type="checkbox" id="autodiag-skip-plugins">
                <span class="toggle-slider"></span>
            </label>
        </div>
    </div>
    
    <div class="settings-actions">
        <button type="button" id="autodiag-save-btn" class="btn btn-primary" data-i18n="save_settings">
            💾 Save Settings
        </button>
        <span id="autodiag-save-status" class="save-status"></span>
    </div>
</div>
'''

    def get_settings_js(self) -> str:
        """Return JavaScript for the settings section."""
        return '''
(function() {
    function initAutodiagSettings() {
        // Main settings
        const enabledCb = document.getElementById("autodiag-enabled");
        const autoRunCb = document.getElementById("autodiag-auto-run");
        const confidenceCb = document.getElementById("autodiag-show-confidence");
        const portInput = document.getElementById("autodiag-port");
        const timeoutInput = document.getElementById("autodiag-settings-timeout");
        
        // Scenario options
        const skipCliCb = document.getElementById("autodiag-skip-cli");
        const skipApiCb = document.getElementById("autodiag-skip-api");
        const skipPluginsCb = document.getElementById("autodiag-skip-plugins");
        
        // Save button
        const saveBtn = document.getElementById("autodiag-save-btn");
        const saveStatus = document.getElementById("autodiag-save-status");
        
        // Load saved settings
        loadSetting(enabledCb, "autodiag_enabled", true);
        loadSetting(autoRunCb, "autodiag_auto_run", false);
        loadSetting(confidenceCb, "autodiag_show_confidence", true);
        loadSetting(portInput, "autodiag_port", "8081");
        loadSetting(timeoutInput, "autodiag_timeout", "30");
        loadSetting(skipCliCb, "autodiag_skip_cli", false);
        loadSetting(skipApiCb, "autodiag_skip_api", false);
        loadSetting(skipPluginsCb, "autodiag_skip_plugins", false);
        
        // Bind save button
        if (saveBtn) {
            saveBtn.addEventListener("click", () => {
                saveAllSettings();
                showSaveStatus(saveStatus, true);
            });
        }
    }
    
    function saveAllSettings() {
        // Save all settings to localStorage
        const settings = [
            { id: "autodiag-enabled", key: "autodiag_enabled", type: "checkbox" },
            { id: "autodiag-auto-run", key: "autodiag_auto_run", type: "checkbox" },
            { id: "autodiag-show-confidence", key: "autodiag_show_confidence", type: "checkbox" },
            { id: "autodiag-port", key: "autodiag_port", type: "text" },
            { id: "autodiag-settings-timeout", key: "autodiag_timeout", type: "text" },
            { id: "autodiag-skip-cli", key: "autodiag_skip_cli", type: "checkbox" },
            { id: "autodiag-skip-api", key: "autodiag_skip_api", type: "checkbox" },
            { id: "autodiag-skip-plugins", key: "autodiag_skip_plugins", type: "checkbox" },
        ];
        
        for (const s of settings) {
            const el = document.getElementById(s.id);
            if (el) {
                const value = s.type === "checkbox" ? el.checked : el.value;
                localStorage.setItem(s.key, value);
            }
        }
        
        // Notify UI view if it's listening
        if (typeof window.AutodiagPlugin !== "undefined" && window.AutodiagPlugin.onSettingsChange) {
            window.AutodiagPlugin.onSettingsChange("all", null);
        }
    }
    
    function showSaveStatus(el, success) {
        if (!el) return;
        el.textContent = success ? "✓ Saved" : "✗ Error";
        el.className = "save-status " + (success ? "success" : "error");
        setTimeout(() => { el.textContent = ""; el.className = "save-status"; }, 2000);
    }
    
    function loadSetting(el, key, defaultValue) {
        if (!el) return;
        const saved = localStorage.getItem(key);
        
        if (el.type === "checkbox") {
            if (saved !== null) {
                el.checked = saved === "true";
            } else {
                el.checked = defaultValue === true;
            }
        } else {
            el.value = saved || defaultValue;
        }
    }
    
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initAutodiagSettings);
    } else {
        initAutodiagSettings();
    }
})();
'''
