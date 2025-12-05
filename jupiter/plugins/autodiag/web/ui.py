"""
Autodiag Plugin - Web UI
========================

HTML and JavaScript templates for the autodiag plugin UI.

Version: 1.4.0

Changelog:
- v1.4.0: Synchronized JS with HTML IDs, fixed tab switching, added quick settings bindings
- v1.3.0: Added 2-column layout with sidebar (help, settings, legend), restored scenarios table
- v1.2.0: Fixed API URLs (/diag/run, /diag/health), added inline CSS injection
- v1.1.0: Initial Bridge v2 implementation
"""

from __future__ import annotations


def get_ui_html() -> str:
    """Return HTML for the main autodiag view with 2-column layout."""
    return '''
<div class="autodiag-wrapper" id="autodiag-view">
    <!-- MAIN CONTENT COLUMN -->
    <div class="autodiag-main">
        <!-- Header -->
        <div class="view-header">
            <div class="header-left">
                <p class="eyebrow" data-i18n="autodiag_eyebrow">Self-Diagnostic</p>
                <h2 data-i18n="autodiag_title">🔬 Autodiag Analysis</h2>
            </div>
            <div class="header-actions">
                <button id="autodiag-run-btn" class="btn btn-primary btn-lg">
                    🚀 <span data-i18n="autodiag_run">Run Autodiag</span>
                </button>
                <button id="autodiag-export-btn" class="btn btn-secondary">
                    📋 <span data-i18n="autodiag_export">Export</span>
                </button>
                <button id="autodiag-refresh-btn" class="btn btn-secondary btn-icon-only" title="Refresh">
                    🔄
                </button>
            </div>
        </div>
        
        <!-- Status Messages -->
        <div class="autodiag-status-area">
            <div class="status-card info-card" id="autodiag-idle">
                <div class="status-icon">💤</div>
                <div class="status-content">
                    <p data-i18n="autodiag_idle">No autodiag analysis has been run yet.</p>
                    <p class="muted" data-i18n="autodiag_idle_hint">Click "Run Autodiag" to start the analysis.</p>
                </div>
            </div>
            
            <div class="status-card warning-card hidden" id="autodiag-running">
                <div class="status-icon spinning">⏳</div>
                <div class="status-content">
                    <p data-i18n="autodiag_running">Autodiag is running...</p>
                    <p class="muted" data-i18n="autodiag_running_hint">Testing CLI, API, and plugin scenarios.</p>
                    <div class="progress-container">
                        <div class="progress-bar" id="autodiag-progress"></div>
                    </div>
                </div>
            </div>
            
            <div class="status-card error-card hidden" id="autodiag-error">
                <div class="status-icon">❌</div>
                <div class="status-content">
                    <p data-i18n="autodiag_error">Autodiag failed.</p>
                    <p class="muted" id="autodiag-error-msg"></p>
                </div>
            </div>
        </div>
        
        <!-- Stats Dashboard -->
        <div class="autodiag-dashboard hidden" id="autodiag-stats">
            <div class="stat-card stat-success">
                <div class="stat-icon">✅</div>
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-fp-count">0</span>
                    <span class="stat-label" data-i18n="autodiag_false_positives">False Positives</span>
                </div>
            </div>
            <div class="stat-card stat-warning">
                <div class="stat-icon">⚠️</div>
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-unused-count">0</span>
                    <span class="stat-label" data-i18n="autodiag_truly_unused">Truly Unused</span>
                </div>
            </div>
            <div class="stat-card stat-info">
                <div class="stat-icon">📊</div>
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-accuracy-rate">0%</span>
                    <span class="stat-label" data-i18n="autodiag_accuracy">Accuracy</span>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-scenario-count">0</span>
                    <span class="stat-label" data-i18n="autodiag_scenarios">Scenarios</span>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-info">
                    <span class="stat-value" id="autodiag-duration">0s</span>
                    <span class="stat-label" data-i18n="autodiag_duration">Duration</span>
                </div>
            </div>
        </div>
        
        <!-- Tabs Navigation -->
        <div class="autodiag-tabs hidden" id="autodiag-tabs">
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
        <div class="tab-content active" id="tab-scenarios">
            <div class="panel">
                <div class="panel-header">
                    <h3 data-i18n="autodiag_scenarios_title">Executed Scenarios</h3>
                    <div class="filter-controls">
                        <select id="autodiag-scenario-filter" class="filter-select">
                            <option value="all" data-i18n="filter_all">All</option>
                            <option value="passed" data-i18n="filter_passed">Passed</option>
                            <option value="failed" data-i18n="filter_failed">Failed</option>
                            <option value="skipped" data-i18n="filter_skipped">Skipped</option>
                        </select>
                    </div>
                </div>
                <div class="table-container">
                    <table class="data-table" id="autodiag-scenarios-table">
                        <thead>
                            <tr>
                                <th data-i18n="autodiag_th_scenario">Scenario</th>
                                <th data-i18n="autodiag_th_type">Type</th>
                                <th data-i18n="autodiag_th_status">Status</th>
                                <th data-i18n="autodiag_th_duration">Duration</th>
                                <th data-i18n="autodiag_th_error">Error</th>
                                <th data-i18n="autodiag_th_triggered">Functions</th>
                            </tr>
                        </thead>
                        <tbody id="autodiag-scenarios-body">
                            <tr>
                                <td colspan="6" class="empty-state" data-i18n="autodiag_no_scenarios">No scenarios executed yet.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Tab Content: False Positives -->
        <div class="tab-content hidden" id="tab-false-positives">
            <div class="panel">
                <div class="panel-header">
                    <h3 data-i18n="autodiag_fp_title">False Positives Detected</h3>
                    <div class="filter-controls">
                        <input type="text" id="autodiag-fp-filter" class="filter-input" placeholder="Filter..." data-i18n-placeholder="autodiag_filter_placeholder">
                    </div>
                </div>
                <p class="panel-description" data-i18n="autodiag_fp_description">
                    Functions marked as "unused" but actually executed during tests.
                </p>
                <div class="table-container">
                    <table class="data-table" id="autodiag-fp-table">
                        <thead>
                            <tr>
                                <th data-i18n="autodiag_th_function">Function</th>
                                <th data-i18n="autodiag_th_file">File</th>
                                <th data-i18n="autodiag_th_reason">Reason</th>
                                <th data-i18n="autodiag_th_triggered_by">Triggered By</th>
                            </tr>
                        </thead>
                        <tbody id="autodiag-fp-body">
                            <tr>
                                <td colspan="4" class="empty-state" data-i18n="autodiag_no_fp">No false positives detected.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Tab Content: Unused -->
        <div class="tab-content hidden" id="tab-unused">
            <div class="panel">
                <h3 data-i18n="autodiag_unused_title">Truly Unused Functions</h3>
                <p class="panel-description" data-i18n="autodiag_unused_description">
                    Functions confirmed as unused - safe candidates for removal.
                </p>
                <div id="autodiag-unused-list" class="function-grid">
                    <p class="empty-state" data-i18n="autodiag_no_unused">No truly unused functions detected.</p>
                </div>
            </div>
        </div>
        
        <!-- Tab Content: Confidence -->
        <div class="tab-content hidden" id="tab-confidence">
            <div class="panel">
                <div class="panel-header">
                    <h3 data-i18n="autodiag_confidence_title">Function Usage Confidence</h3>
                    <div class="filter-controls">
                        <input type="text" id="autodiag-conf-filter" class="filter-input" placeholder="Filter..." data-i18n-placeholder="autodiag_filter_placeholder">
                        <select id="autodiag-conf-status-filter" class="filter-select">
                            <option value="all" data-i18n="filter_all">All</option>
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
                <p class="panel-description" data-i18n="autodiag_confidence_description">
                    Detailed confidence scores for function usage detection.
                </p>
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
                        <tbody id="autodiag-confidence-body">
                            <tr>
                                <td colspan="5" class="empty-state" data-i18n="autodiag_no_confidence">No confidence data available.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- Tab Content: Recommendations -->
        <div class="tab-content hidden" id="tab-recommendations">
            <div class="panel">
                <h3 data-i18n="autodiag_recommendations">Recommendations</h3>
                <div id="autodiag-recommendations-list" class="recommendations-list">
                    <p class="empty-state" data-i18n="autodiag_no_recommendations">No recommendations - everything looks good!</p>
                </div>
            </div>
        </div>
    </div>
    
    <!-- SIDEBAR COLUMN -->
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
                <div class="server-status" id="autodiag-server-status-panel">
                    <span class="status-dot" id="autodiag-status-dot"></span>
                    <span id="autodiag-status-text" data-i18n="autodiag_checking">Checking...</span>
                </div>
                <p class="server-url">
                    <code id="autodiag-server-url">http://127.0.0.1:8081</code>
                </p>
            </div>
        </div>
    </aside>
    
    <!-- Export Modal -->
    <div class="modal hidden" id="autodiag-export-modal">
        <div class="modal-backdrop" onclick="window.closeExportModal && closeExportModal()"></div>
        <div class="modal-content modal-large">
            <div class="modal-header">
                <h3 data-i18n="autodiag_export_title">Export for AI Assistant</h3>
                <button class="modal-close" onclick="window.closeExportModal && closeExportModal()">×</button>
            </div>
            <div class="modal-body">
                <p class="modal-description" data-i18n="autodiag_export_description">
                    Copy this formatted report to share with an AI assistant for code cleanup help.
                </p>
                <textarea id="autodiag-export-content" class="export-textarea" readonly></textarea>
            </div>
            <div class="modal-footer">
                <button id="autodiag-copy-btn" class="btn btn-primary" onclick="window.copyToClipboard && copyToClipboard()">
                    📋 <span data-i18n="copy_to_clipboard">Copy to Clipboard</span>
                </button>
                <button class="btn btn-secondary" onclick="window.closeExportModal && closeExportModal()" data-i18n="close">Close</button>
            </div>
        </div>
    </div>
</div>
'''


def get_ui_js() -> str:
    """Return JavaScript for the main autodiag view."""
    return '''
(function() {
    const AUTODIAG_PORT = parseInt(localStorage.getItem("autodiag_port")) || 8081;
    let currentReport = null;
    
    // ─────────────────────────────────────────────────────────────────────
    // Inline CSS Injection (Plugin-specific styles)
    // ─────────────────────────────────────────────────────────────────────
    
    const AUTODIAG_CSS_ID = "autodiag-plugin-styles";
    const AUTODIAG_CSS = `
        /* Autodiag Plugin Styles v1.3.0 - 2-column layout */
        
        /* Main wrapper - 2 column layout */
        .autodiag-wrapper {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 1.5rem;
            padding: 1.5rem;
            max-width: 1600px;
            margin: 0 auto;
            min-height: calc(100vh - 60px);
        }
        
        @media (max-width: 1200px) {
            .autodiag-wrapper {
                grid-template-columns: 1fr;
            }
            .autodiag-sidebar {
                display: none;
            }
        }
        
        /* Main content column */
        .autodiag-main {
            min-width: 0;
        }
        
        /* Header */
        .autodiag-wrapper .view-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
            gap: 1rem;
        }
        
        .autodiag-wrapper .header-left .eyebrow {
            margin: 0 0 0.25rem 0;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--accent-color, #3b82f6);
        }
        
        .autodiag-wrapper .header-left h2 {
            margin: 0;
            font-size: 1.5rem;
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-wrapper .header-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .autodiag-wrapper .btn-icon-only {
            padding: 0.5rem 0.75rem;
        }
        
        /* Status Area */
        .autodiag-status-area {
            margin-bottom: 1.5rem;
        }
        
        .autodiag-wrapper .status-card {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            border: 1px solid var(--border-color, #3f3f46);
        }
        
        .autodiag-wrapper .status-card.info-card {
            background: var(--bg-secondary, #27272a);
        }
        
        .autodiag-wrapper .status-card.warning-card {
            background: rgba(245, 158, 11, 0.1);
            border-color: var(--warning-color, #f59e0b);
        }
        
        .autodiag-wrapper .status-card.error-card {
            background: rgba(239, 68, 68, 0.1);
            border-color: var(--error-color, #ef4444);
        }
        
        .autodiag-wrapper .status-icon {
            font-size: 2rem;
        }
        
        .autodiag-wrapper .status-icon.spinning {
            animation: autodiag-spin 1s linear infinite;
        }
        
        .autodiag-wrapper .status-content p {
            margin: 0;
        }
        
        .autodiag-wrapper .status-content .muted {
            color: var(--text-secondary, #a1a1aa);
            font-size: 0.875rem;
            margin-top: 0.25rem;
        }
        
        .autodiag-wrapper .progress-container {
            margin-top: 0.75rem;
            height: 4px;
            background: var(--bg-tertiary, #18181b);
            border-radius: 2px;
            overflow: hidden;
        }
        
        .autodiag-wrapper .progress-bar {
            height: 100%;
            background: var(--accent-color, #3b82f6);
            width: 30%;
            animation: autodiag-progress 2s ease-in-out infinite;
        }
        
        @keyframes autodiag-progress {
            0% { width: 0%; margin-left: 0; }
            50% { width: 50%; margin-left: 25%; }
            100% { width: 0%; margin-left: 100%; }
        }
        
        /* Dashboard stats */
        .autodiag-dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .autodiag-wrapper .stat-card {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 1rem;
            background: var(--bg-secondary, #27272a);
            border-radius: 8px;
            border: 1px solid var(--border-color, #3f3f46);
        }
        
        .autodiag-wrapper .stat-card.stat-success {
            border-left: 3px solid var(--success-color, #22c55e);
        }
        
        .autodiag-wrapper .stat-card.stat-warning {
            border-left: 3px solid var(--warning-color, #f59e0b);
        }
        
        .autodiag-wrapper .stat-card.stat-info {
            border-left: 3px solid var(--accent-color, #3b82f6);
        }
        
        .autodiag-wrapper .stat-icon {
            font-size: 1.5rem;
        }
        
        .autodiag-wrapper .stat-info {
            display: flex;
            flex-direction: column;
        }
        
        .autodiag-wrapper .stat-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-wrapper .stat-label {
            font-size: 0.75rem;
            color: var(--text-secondary, #a1a1aa);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        /* Tabs */
        .autodiag-tabs {
            display: flex;
            gap: 0;
            border-bottom: 1px solid var(--border-color, #3f3f46);
            margin-bottom: 1rem;
            overflow-x: auto;
        }
        
        .autodiag-wrapper .tab-btn {
            padding: 0.75rem 1rem;
            background: transparent;
            border: none;
            color: var(--text-secondary, #a1a1aa);
            cursor: pointer;
            font-size: 0.875rem;
            white-space: nowrap;
            border-bottom: 2px solid transparent;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .autodiag-wrapper .tab-btn:hover {
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-wrapper .tab-btn.active {
            color: var(--accent-color, #3b82f6);
            border-bottom-color: var(--accent-color, #3b82f6);
        }
        
        .autodiag-wrapper .tab-badge {
            background: var(--bg-tertiary, #18181b);
            padding: 0.125rem 0.5rem;
            border-radius: 10px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        /* Tab content */
        .autodiag-wrapper .tab-content {
            display: none;
        }
        
        .autodiag-wrapper .tab-content.active {
            display: block;
        }
        
        /* Panel */
        .autodiag-wrapper .panel {
            background: var(--bg-secondary, #27272a);
            border-radius: 8px;
            padding: 1.5rem;
            border: 1px solid var(--border-color, #3f3f46);
        }
        
        .autodiag-wrapper .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.75rem;
        }
        
        .autodiag-wrapper .panel h3 {
            margin: 0;
            font-size: 1rem;
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-wrapper .panel-description {
            margin: 0 0 1rem 0;
            color: var(--text-secondary, #a1a1aa);
            font-size: 0.875rem;
        }
        
        .autodiag-wrapper .filter-controls {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        
        .autodiag-wrapper .filter-input {
            padding: 0.5rem;
            background: var(--bg-tertiary, #18181b);
            border: 1px solid var(--border-color, #3f3f46);
            border-radius: 4px;
            color: var(--text-primary, #e4e4e7);
            font-size: 0.875rem;
            width: 150px;
        }
        
        .autodiag-wrapper .filter-select {
            padding: 0.5rem;
            background: var(--bg-tertiary, #18181b);
            border: 1px solid var(--border-color, #3f3f46);
            border-radius: 4px;
            color: var(--text-primary, #e4e4e7);
            font-size: 0.875rem;
        }
        
        /* Data Table */
        .autodiag-wrapper .table-container {
            overflow-x: auto;
        }
        
        .autodiag-wrapper .data-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .autodiag-wrapper .data-table th,
        .autodiag-wrapper .data-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color, #3f3f46);
        }
        
        .autodiag-wrapper .data-table th {
            background: var(--bg-tertiary, #18181b);
            color: var(--text-secondary, #a1a1aa);
            font-weight: 500;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .autodiag-wrapper .data-table td {
            color: var(--text-primary, #e4e4e7);
            font-size: 0.875rem;
        }
        
        .autodiag-wrapper .data-table code {
            background: var(--bg-tertiary, #18181b);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.85em;
        }
        
        .autodiag-wrapper .data-table tr.row-error {
            background: rgba(239, 68, 68, 0.1);
        }
        
        .autodiag-wrapper .data-table .status-passed {
            color: var(--success-color, #22c55e);
        }
        
        .autodiag-wrapper .data-table .status-failed {
            color: var(--error-color, #ef4444);
        }
        
        .autodiag-wrapper .data-table .status-skipped {
            color: var(--text-secondary, #a1a1aa);
        }
        
        /* Function grid for unused */
        .autodiag-wrapper .function-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 0.75rem;
        }
        
        .autodiag-wrapper .function-card {
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--bg-tertiary, #18181b);
            border-radius: 6px;
            border: 1px solid var(--border-color, #3f3f46);
        }
        
        .autodiag-wrapper .function-card .func-icon {
            font-size: 1.25rem;
        }
        
        .autodiag-wrapper .function-card .func-info {
            flex: 1;
            min-width: 0;
        }
        
        .autodiag-wrapper .function-card .func-name {
            font-family: monospace;
            font-weight: 500;
            color: var(--text-primary, #e4e4e7);
            word-break: break-all;
        }
        
        .autodiag-wrapper .function-card .func-file {
            font-size: 0.75rem;
            color: var(--text-secondary, #a1a1aa);
            word-break: break-all;
        }
        
        /* Recommendations */
        .autodiag-wrapper .recommendations-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .autodiag-wrapper .recommendation-item {
            padding: 0.75rem 1rem;
            background: var(--bg-tertiary, #18181b);
            border-radius: 6px;
            border-left: 3px solid var(--accent-color, #3b82f6);
            color: var(--text-primary, #e4e4e7);
        }
        
        /* Empty state */
        .autodiag-wrapper .empty-state {
            color: var(--text-secondary, #a1a1aa);
            text-align: center;
            padding: 2rem;
            font-style: italic;
        }
        
        /* SIDEBAR */
        .autodiag-sidebar {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        
        .autodiag-sidebar .sidebar-panel {
            background: var(--bg-secondary, #27272a);
            border-radius: 8px;
            border: 1px solid var(--border-color, #3f3f46);
            overflow: hidden;
        }
        
        .autodiag-sidebar .panel-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1rem;
            background: var(--bg-tertiary, #18181b);
            border-bottom: 1px solid var(--border-color, #3f3f46);
        }
        
        .autodiag-sidebar .panel-header .panel-icon {
            font-size: 1rem;
        }
        
        .autodiag-sidebar .panel-header h4 {
            margin: 0;
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-sidebar .panel-content {
            padding: 1rem;
        }
        
        /* Sidebar settings */
        .autodiag-sidebar .setting-row {
            margin-bottom: 0.75rem;
        }
        
        .autodiag-sidebar .setting-row:last-child {
            margin-bottom: 0;
        }
        
        .autodiag-sidebar .toggle-label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
            font-size: 0.875rem;
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-sidebar .toggle-label input[type="checkbox"] {
            width: 16px;
            height: 16px;
            accent-color: var(--accent-color, #3b82f6);
        }
        
        .autodiag-sidebar .input-label {
            font-size: 0.875rem;
            color: var(--text-secondary, #a1a1aa);
            margin-right: 0.5rem;
        }
        
        .autodiag-sidebar .setting-input-sm {
            width: 60px;
            padding: 0.25rem 0.5rem;
            background: var(--bg-tertiary, #18181b);
            border: 1px solid var(--border-color, #3f3f46);
            border-radius: 4px;
            color: var(--text-primary, #e4e4e7);
            font-size: 0.875rem;
        }
        
        /* Help panel */
        .autodiag-sidebar .help-text {
            margin: 0 0 1rem 0;
            font-size: 0.875rem;
            color: var(--text-secondary, #a1a1aa);
            line-height: 1.5;
        }
        
        .autodiag-sidebar .help-steps {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .autodiag-sidebar .help-step {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-primary, #e4e4e7);
        }
        
        .autodiag-sidebar .step-icon {
            font-size: 1rem;
        }
        
        /* Legend */
        .autodiag-sidebar .legend-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            margin-bottom: 0.5rem;
        }
        
        .autodiag-sidebar .legend-item:last-child {
            margin-bottom: 0;
        }
        
        .autodiag-sidebar .legend-badge {
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            min-width: 60px;
            text-align: center;
        }
        
        .autodiag-sidebar .badge-used {
            background: rgba(34, 197, 94, 0.2);
            color: var(--success-color, #22c55e);
        }
        
        .autodiag-sidebar .badge-likely {
            background: rgba(59, 130, 246, 0.2);
            color: var(--accent-color, #3b82f6);
        }
        
        .autodiag-sidebar .badge-possibly {
            background: rgba(245, 158, 11, 0.2);
            color: var(--warning-color, #f59e0b);
        }
        
        .autodiag-sidebar .badge-unused {
            background: rgba(239, 68, 68, 0.2);
            color: var(--error-color, #ef4444);
        }
        
        .autodiag-sidebar .legend-desc {
            font-size: 0.8rem;
            color: var(--text-secondary, #a1a1aa);
        }
        
        /* Server status */
        .autodiag-sidebar .server-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        .autodiag-sidebar .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--text-secondary, #a1a1aa);
        }
        
        .autodiag-sidebar .status-dot.online {
            background: var(--success-color, #22c55e);
            box-shadow: 0 0 6px var(--success-color, #22c55e);
        }
        
        .autodiag-sidebar .status-dot.offline {
            background: var(--error-color, #ef4444);
        }
        
        .autodiag-sidebar .server-url {
            margin: 0;
        }
        
        .autodiag-sidebar .server-url code {
            font-size: 0.75rem;
            color: var(--text-secondary, #a1a1aa);
            background: var(--bg-tertiary, #18181b);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }
        
        /* Hidden utility */
        .hidden {
            display: none !important;
        }
        
        /* Spinner animation */
        @keyframes autodiag-spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        
        /* Export modal */
        .autodiag-wrapper .export-textarea {
            width: 100%;
            min-height: 300px;
            padding: 1rem;
            background: var(--bg-tertiary, #18181b);
            border: 1px solid var(--border-color, #3f3f46);
            border-radius: 6px;
            color: var(--text-primary, #e4e4e7);
            font-family: monospace;
            font-size: 0.875rem;
            resize: vertical;
        }
    `;
    
    function injectCSS() {
        if (document.getElementById(AUTODIAG_CSS_ID)) return;
        const style = document.createElement("style");
        style.id = AUTODIAG_CSS_ID;
        style.textContent = AUTODIAG_CSS;
        document.head.appendChild(style);
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Initialization
    // ─────────────────────────────────────────────────────────────────────
    
    function init() {
        injectCSS();
        bindEvents();
        checkDiagServerHealth();
        refreshData();
    }
    
    function bindEvents() {
        const runBtn = document.getElementById("autodiag-run-btn");
        const refreshBtn = document.getElementById("autodiag-refresh-btn");
        const exportBtn = document.getElementById("autodiag-export-btn");
        const scenarioFilter = document.getElementById("autodiag-scenario-filter");
        const loadConfBtn = document.getElementById("autodiag-load-confidence-btn");
        
        if (runBtn) runBtn.addEventListener("click", runAutodiag);
        if (refreshBtn) refreshBtn.addEventListener("click", refreshData);
        if (exportBtn) exportBtn.addEventListener("click", showExportModal);
        if (scenarioFilter) scenarioFilter.addEventListener("change", filterScenarios);
        if (loadConfBtn) loadConfBtn.addEventListener("click", loadConfidenceData);
        
        // Tab switching
        document.querySelectorAll(".tab-btn").forEach(tab => {
            tab.addEventListener("click", () => switchTab(tab.dataset.tab));
        });
        
        // Quick settings bindings
        bindQuickSettings();
    }
    
    function bindQuickSettings() {
        const skipCliToggle = document.getElementById("autodiag-opt-skip-cli");
        const skipApiToggle = document.getElementById("autodiag-opt-skip-api");
        const skipPluginsToggle = document.getElementById("autodiag-opt-skip-plugins");
        
        // Load saved values
        if (skipCliToggle) {
            skipCliToggle.checked = localStorage.getItem("autodiag_skip_cli") === "true";
            skipCliToggle.addEventListener("change", () => {
                localStorage.setItem("autodiag_skip_cli", skipCliToggle.checked);
            });
        }
        if (skipApiToggle) {
            skipApiToggle.checked = localStorage.getItem("autodiag_skip_api") === "true";
            skipApiToggle.addEventListener("change", () => {
                localStorage.setItem("autodiag_skip_api", skipApiToggle.checked);
            });
        }
        if (skipPluginsToggle) {
            skipPluginsToggle.checked = localStorage.getItem("autodiag_skip_plugins") === "true";
            skipPluginsToggle.addEventListener("change", () => {
                localStorage.setItem("autodiag_skip_plugins", skipPluginsToggle.checked);
            });
        }
    }
    
    function switchTab(tabId) {
        document.querySelectorAll(".tab-btn").forEach(t => t.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => {
            c.classList.remove("active");
            c.classList.add("hidden");
        });
        
        const tab = document.querySelector(`[data-tab="${tabId}"]`);
        const content = document.getElementById(`tab-${tabId}`);
        
        if (tab) tab.classList.add("active");
        if (content) {
            content.classList.add("active");
            content.classList.remove("hidden");
        }
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Server Communication
    // ─────────────────────────────────────────────────────────────────────
    
    async function checkDiagServerHealth() {
        const statusDot = document.getElementById("autodiag-status-dot");
        const statusText = document.getElementById("autodiag-server-status-text");
        
        try {
            const response = await fetch(`http://localhost:${AUTODIAG_PORT}/diag/health`, {
                method: "GET",
                signal: AbortSignal.timeout(3000)
            });
            
            if (response.ok) {
                if (statusDot) {
                    statusDot.classList.remove("offline");
                    statusDot.classList.add("online");
                }
                if (statusText) statusText.textContent = "Online";
            } else {
                throw new Error("Server returned error");
            }
        } catch (err) {
            if (statusDot) {
                statusDot.classList.remove("online");
                statusDot.classList.add("offline");
            }
            if (statusText) statusText.textContent = "Offline";
            console.warn("[AutodiagPlugin] Server offline:", err.message);
        }
    }
    
    async function runAutodiag() {
        const runBtn = document.getElementById("autodiag-run-btn");
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="btn-icon spinner">⏳</span> Running...';
        }
        
        try {
            // Get options from settings
            const options = {
                skip_cli: localStorage.getItem("autodiag_skip_cli") === "true",
                skip_api: localStorage.getItem("autodiag_skip_api") === "true",
                skip_plugins: localStorage.getItem("autodiag_skip_plugins") === "true",
                timeout: parseInt(localStorage.getItem("autodiag_timeout")) || 30
            };
            
            const response = await fetch(`http://localhost:${AUTODIAG_PORT}/diag/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(options)
            });
            
            if (!response.ok) throw new Error(`Server error: ${response.status}`);
            
            const data = await response.json();
            currentReport = data;
            updateUI(data);
            
            // Notify Jupiter API
            await fetch("/api/plugins/autodiag/report", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            }).catch(() => {});
            
        } catch (err) {
            console.error("[AutodiagPlugin] Run failed:", err);
            showError("Failed to run autodiag: " + err.message);
        } finally {
            if (runBtn) {
                runBtn.disabled = false;
                runBtn.innerHTML = '<span class="btn-icon">▶</span> Run Autodiag';
            }
        }
    }
    
    async function refreshData() {
        try {
            // Try to get cached report from Jupiter API
            const response = await fetch("/api/plugins/autodiag/state");
            if (response.ok) {
                const data = await response.json();
                if (data.last_report && Object.keys(data.last_report).length > 0) {
                    currentReport = data.last_report;
                    updateUI(data.last_report);
                }
            }
        } catch (err) {
            console.warn("[AutodiagPlugin] Refresh failed:", err.message);
        }
        
        checkDiagServerHealth();
    }
    
    async function loadConfidenceData() {
        // Load confidence data if available in current report
        if (!currentReport || !currentReport.confidence_data) return;
        renderConfidenceTable(currentReport.confidence_data);
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // UI Rendering
    // ─────────────────────────────────────────────────────────────────────
    
    function updateUI(data) {
        // Show stats dashboard and tabs
        const statsEl = document.getElementById("autodiag-stats");
        const tabsEl = document.getElementById("autodiag-tabs");
        if (statsEl) statsEl.classList.remove("hidden");
        if (tabsEl) tabsEl.classList.remove("hidden");
        
        // Update dashboard stats
        const fp = data.false_positives?.length || 0;
        const unused = data.truly_unused?.length || 0;
        const scenarios = data.scenarios?.length || 0;
        const total = fp + unused;
        const accuracy = total > 0 ? Math.round((fp / total) * 100) : 0;
        
        updateElement("autodiag-fp-count", fp);
        updateElement("autodiag-unused-count", unused);
        updateElement("autodiag-scenario-count", scenarios);
        updateElement("autodiag-accuracy-rate", accuracy + "%");
        updateElement("autodiag-duration", data.execution_time ? data.execution_time.toFixed(2) + "s" : "0s");
        
        // Render sections
        renderScenarios(data.scenarios || []);
        renderFalsePositives(data.false_positives || []);
        renderTrulyUnused(data.truly_unused || []);
        renderRecommendations(data.recommendations || []);
        
        if (data.confidence_data) {
            renderConfidenceTable(data.confidence_data);
        }
    }
    
    function updateElement(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
    
    function renderScenarios(scenarios) {
        const tbody = document.getElementById("autodiag-scenarios-body");
        const countEl = document.getElementById("autodiag-tab-scenarios-count");
        if (!tbody) return;
        
        if (countEl) countEl.textContent = scenarios.length;
        
        if (!scenarios.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No scenarios executed yet.</td></tr>';
            return;
        }
        
        let html = "";
        for (const s of scenarios) {
            const statusClass = s.status === "passed" ? "success" : s.status === "failed" ? "error" : "neutral";
            const statusIcon = s.status === "passed" ? "✓" : s.status === "failed" ? "✗" : "⊘";
            const triggered = Array.isArray(s.triggered_functions) ? s.triggered_functions.length : 0;
            
            html += `
            <tr data-status="${s.status}">
                <td><code>${escapeHtml(s.name)}</code></td>
                <td><span class="badge badge-type">${escapeHtml(s.type || "test")}</span></td>
                <td><span class="status-badge status-${statusClass}">${statusIcon} ${escapeHtml(s.status)}</span></td>
                <td>${s.duration ? s.duration.toFixed(2) + "s" : "-"}</td>
                <td><span class="error-text">${escapeHtml(s.error || "-")}</span></td>
                <td><span class="badge">${triggered}</span></td>
            </tr>`;
        }
        tbody.innerHTML = html;
    }
    
    function filterScenarios() {
        const filter = document.getElementById("autodiag-scenario-filter")?.value || "all";
        const rows = document.querySelectorAll("#autodiag-scenarios-body tr[data-status]");
        
        rows.forEach(row => {
            if (filter === "all" || row.dataset.status === filter) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    }
    
    function renderFalsePositives(functions) {
        const tbody = document.getElementById("autodiag-fp-body");
        const countEl = document.getElementById("autodiag-tab-fp-count");
        if (!tbody) return;
        
        if (countEl) countEl.textContent = functions.length;
        
        if (!functions.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No false positives detected.</td></tr>';
            return;
        }
        
        let html = "";
        for (const f of functions) {
            const triggeredBy = f.triggered_by || f.scenario || "dynamic execution";
            html += `
            <tr>
                <td><code class="function-name">${escapeHtml(f.name)}</code></td>
                <td><span class="file-path">${escapeHtml(f.file || "")}${f.line ? ":" + f.line : ""}</span></td>
                <td><span class="badge badge-success">Dynamic use detected</span></td>
                <td><span class="trigger-info">${escapeHtml(triggeredBy)}</span></td>
            </tr>`;
        }
        tbody.innerHTML = html;
    }
    
    function renderTrulyUnused(functions) {
        const container = document.getElementById("autodiag-unused-list");
        const countEl = document.getElementById("autodiag-tab-unused-count");
        if (!container) return;
        
        if (countEl) countEl.textContent = functions.length;
        
        if (!functions.length) {
            container.innerHTML = '<p class="empty-state">No truly unused functions detected.</p>';
            return;
        }
        
        let html = '<div class="function-grid">';
        for (const f of functions) {
            html += `
            <div class="function-card function-unused">
                <div class="function-header">
                    <span class="function-icon">🔴</span>
                    <code class="function-name">${escapeHtml(f.name)}</code>
                </div>
                <div class="function-details">
                    <span class="file-path">${escapeHtml(f.file || "")}</span>
                    ${f.line ? `<span class="line-number">line ${f.line}</span>` : ""}
                </div>
                <span class="function-badge badge-warning">Safe to remove</span>
            </div>`;
        }
        html += '</div>';
        container.innerHTML = html;
    }
    
    function renderRecommendations(recommendations) {
        const container = document.getElementById("autodiag-recommendations-list");
        if (!container) return;
        
        if (!recommendations.length) {
            container.innerHTML = '<p class="empty-state">No recommendations - everything looks good!</p>';
            return;
        }
        
        let html = '<ul class="recommendation-list">';
        for (const r of recommendations) {
            const icon = r.includes("remove") ? "🗑️" : r.includes("test") ? "🧪" : "💡";
            html += `<li class="recommendation-item"><span class="rec-icon">${icon}</span> ${escapeHtml(r)}</li>`;
        }
        html += '</ul>';
        container.innerHTML = html;
    }
    
    function renderConfidenceTable(data) {
        const tbody = document.getElementById("autodiag-confidence-body");
        if (!tbody) return;
        
        if (!data || !data.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No confidence data available.</td></tr>';
            return;
        }
        
        let html = "";
        for (const item of data) {
            const confidence = Math.round(item.confidence * 100);
            const statusClass = confidence >= 80 ? "success" : confidence >= 50 ? "warning" : "error";
            
            html += `
            <tr>
                <td><code>${escapeHtml(item.name)}</code></td>
                <td>${escapeHtml(item.file || "")}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill progress-${statusClass}" style="width: ${confidence}%"></div>
                        <span class="progress-label">${confidence}%</span>
                    </div>
                </td>
                <td><span class="status-badge status-${statusClass}">${item.status || "unknown"}</span></td>
            </tr>`;
        }
        tbody.innerHTML = html;
    }
    
    // ─────────────────────────────────────────────────────────────────────
    // Export Functions
    // ─────────────────────────────────────────────────────────────────────
    
    function generateExportText() {
        if (!currentReport) return "No autodiag data available.";
        
        const falsePositives = currentReport.false_positives || [];
        const trulyUnused = currentReport.truly_unused || [];
        const scenarios = currentReport.scenarios || [];
        const recommendations = currentReport.recommendations || [];
        
        let text = "# Jupiter Autodiag Report\\n\\n";
        text += `Generated: ${new Date().toISOString()}\\n\\n`;
        
        // Summary
        text += "## Summary\\n\\n";
        text += `- **False Positives Found:** ${falsePositives.length}\\n`;
        text += `- **Truly Unused Functions:** ${trulyUnused.length}\\n`;
        text += `- **Scenarios Executed:** ${scenarios.length}\\n\\n`;
        
        // False Positives
        if (falsePositives.length > 0) {
            text += "## False Positives (Do NOT remove)\\n\\n";
            text += "These functions were marked as unused by static analysis but are actually used:\\n\\n";
            for (const f of falsePositives) {
                text += `- \\`${f.name}\\` in \\`${f.file || "unknown"}\\`\\n`;
            }
            text += "\\n";
        }
        
        // Truly Unused
        if (trulyUnused.length > 0) {
            text += "## Truly Unused (Safe to remove)\\n\\n";
            text += "These functions are confirmed unused and can be safely removed:\\n\\n";
            for (const f of trulyUnused) {
                text += `- \\`${f.name}\\` in \\`${f.file || "unknown"}\\` (line ${f.line || "?"})\\n`;
            }
            text += "\\n";
        }
        
        // Recommendations
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
    // Helpers
    // ─────────────────────────────────────────────────────────────────────
    
    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
    
    function showError(message) {
        // Show error in summary area
        const summary = document.getElementById("autodiag-summary-content");
        if (summary) {
            summary.innerHTML = `<div class="error-message">${escapeHtml(message)}</div>`;
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
    
    // Expose to window for external access
    window.AutodiagPlugin = {
        init,
        runAutodiag,
        refreshData,
        loadConfidenceData,
        showExportModal,
        closeExportModal: closeExportModal,
        copyToClipboard: copyToClipboard,
        getCurrentReport: () => currentReport
    };
    
    // Make modal functions global for onclick handlers
    window.closeExportModal = closeExportModal;
    window.copyToClipboard = copyToClipboard;
})();
'''


def get_settings_html() -> str:
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


def get_settings_js() -> str:
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
