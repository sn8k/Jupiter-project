"""
Pylance Analyzer - Legacy UI Components

This module provides HTML and JavaScript for the legacy UI rendering system.
In the v2 architecture, these are served via the panels/* JS files.

@version 1.0.0
"""

from __future__ import annotations


def get_ui_html() -> str:
    """Return HTML content for the Pylance view (legacy API)."""
    return _UI_HTML


def get_ui_js() -> str:
    """Return JavaScript code for the Pylance view (legacy API)."""
    return _UI_JS


def get_settings_html() -> str:
    """Return HTML content for the settings frame (legacy API)."""
    return _SETTINGS_HTML


def get_settings_js() -> str:
    """Return JavaScript code for the settings frame (legacy API)."""
    return _SETTINGS_JS


# =============================================================================
# UI HTML TEMPLATE
# =============================================================================

_UI_HTML = """
<section class="view-section" id="pylance-section">
    <header class="section-header">
        <div>
            <p class="eyebrow" data-i18n="pylance_eyebrow">Type Analysis</p>
            <h2 data-i18n="pylance_title">Pylance / Pyright Diagnostics</h2>
            <p class="subtitle" data-i18n="pylance_subtitle">Static type checking powered by Pyright.</p>
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" id="pylance-refresh-btn">🔄 <span data-i18n="pylance_refresh">Refresh</span></button>
            <button class="btn btn-secondary" id="pylance-export-btn">📋 <span data-i18n="pylance_export">Export</span></button>
        </div>
    </header>
    
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
        <p class="warning-text">⚠️ <span data-i18n="pylance_not_installed">Pyright is not installed.</span></p>
        <p class="muted">Install with: <code>pip install pyright</code></p>
    </div>
    
    <div class="card error-card" id="pylance-error" style="display: none;">
        <p class="error-text">❌ <span data-i18n="pylance_error">Analysis failed.</span></p>
        <p class="muted" id="pylance-error-msg"></p>
    </div>

    <div class="card info-card" id="pylance-no-data" style="display: none;">
        <p>ℹ️ <span data-i18n="pylance_no_data">No Pylance data available.</span></p>
        <p class="muted">Run a scan to analyze your Python files.</p>
    </div>
    
    <div class="card info-card" id="pylance-no-python" style="display: none;">
        <p>ℹ️ <span data-i18n="pylance_no_python">No Python files in this project.</span></p>
    </div>

    <div class="card success-card" id="pylance-all-good" style="display: none;">
        <p>✅ <span data-i18n="pylance_all_good">No type errors found!</span></p>
    </div>
</section>

<!-- Files List Section -->
<section class="view-section" id="pylance-files-section" style="display: none;">
    <h3 data-i18n="pylance_files_title">Files with Issues</h3>
    <div class="filter-bar">
        <input type="text" id="pylance-filter" class="filter-input" placeholder="Filter...">
        <select id="pylance-severity-filter" class="filter-select">
            <option value="all">All</option>
            <option value="error">Errors only</option>
            <option value="warning">Warnings only</option>
        </select>
    </div>
    <div class="table-container">
        <table class="data-table" id="pylance-files-table">
            <thead>
                <tr>
                    <th>File</th>
                    <th>Errors</th>
                    <th>Warnings</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="pylance-files-body"></tbody>
        </table>
    </div>
</section>

<!-- File Details Section -->
<section class="view-section" id="pylance-details-section" style="display: none;">
    <h3 id="pylance-details-title">Diagnostics</h3>
    <div class="details-actions">
        <button class="btn btn-secondary" id="pylance-back-btn">← Back</button>
        <button class="btn btn-secondary" id="pylance-export-file-btn">📋 Export</button>
    </div>
    <div class="table-container">
        <table class="data-table" id="pylance-diagnostics-table">
            <thead>
                <tr>
                    <th>Line</th>
                    <th>Severity</th>
                    <th>Message</th>
                    <th>Rule</th>
                </tr>
            </thead>
            <tbody id="pylance-diagnostics-body"></tbody>
        </table>
    </div>
</section>

<!-- Export Modal -->
<div class="modal hidden" id="pylance-export-modal">
    <div class="modal-content" style="max-width: 800px;">
        <header class="modal-header">
            <h3>Export Pylance Results</h3>
            <button class="close-btn" data-action="close-pylance-export">&times;</button>
        </header>
        <div class="modal-body">
            <p class="muted">Copy this report for your AI coding assistant:</p>
            <textarea id="pylance-export-content" class="export-textarea" readonly rows="20"></textarea>
        </div>
        <footer class="modal-footer">
            <button class="btn btn-primary" id="pylance-copy-btn">📋 Copy</button>
            <button class="btn btn-secondary" data-action="close-pylance-export">Close</button>
        </footer>
    </div>
</div>
"""


# =============================================================================
# UI JAVASCRIPT
# =============================================================================

_UI_JS = """
(function() {
    const controller = {
        data: null,
        currentFilePath: null,
        
        getApiBaseUrl() {
            return (typeof state !== 'undefined' && state.apiBaseUrl) 
                ? state.apiBaseUrl 
                : window.location.protocol + '//' + window.location.hostname + ':8000';
        },
        
        $(id) { return document.getElementById(id); },
        
        async init() {
            console.log('[Pylance] Init');
            await this.loadData();
            this.bindEvents();
        },
        
        async loadData() {
            try {
                const apiBase = this.getApiBaseUrl();
                const token = localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
                const resp = await fetch(`${apiBase}/reports/last`, {
                    headers: token ? { 'Authorization': 'Bearer ' + token } : {}
                });
                
                if (!resp.ok) { this.showNoData(); return; }
                
                const report = await resp.json();
                if (!report.pylance) { this.showNoData(); return; }
                
                if (report.pylance.status === 'error') {
                    if (report.pylance.reason === 'pyright_not_available') {
                        this.showNotAvailable();
                    } else {
                        this.showError(report.pylance.message || report.pylance.reason);
                    }
                    return;
                }
                
                if (report.pylance.status === 'skipped') {
                    if (report.pylance.reason === 'no_python_files') {
                        this.showNoPythonFiles();
                    } else {
                        this.showNoData();
                    }
                    return;
                }
                
                if (report.pylance.status !== 'ok' || !report.pylance.summary) {
                    this.showNoData();
                    return;
                }
                
                this.data = report.pylance.summary;
                this.render();
            } catch (err) {
                console.error('[Pylance] Load error:', err);
                this.showNoData();
            }
        },
        
        hideAllStatus() {
            ['pylance-no-data', 'pylance-not-available', 'pylance-error', 
             'pylance-all-good', 'pylance-no-python', 'pylance-files-section']
                .forEach(id => { const el = this.$(id); if (el) el.style.display = 'none'; });
        },
        
        showNoData() { this.hideAllStatus(); const el = this.$('pylance-no-data'); if (el) el.style.display = 'block'; },
        showNotAvailable() { this.hideAllStatus(); const el = this.$('pylance-not-available'); if (el) el.style.display = 'block'; },
        showNoPythonFiles() { this.hideAllStatus(); const el = this.$('pylance-no-python'); if (el) el.style.display = 'block'; },
        showAllGood() { this.hideAllStatus(); const el = this.$('pylance-all-good'); if (el) el.style.display = 'block'; },
        showError(msg) {
            this.hideAllStatus();
            const el = this.$('pylance-error');
            const msgEl = this.$('pylance-error-msg');
            if (el) el.style.display = 'block';
            if (msgEl) msgEl.textContent = msg;
        },
        
        render() {
            if (!this.data) return;
            
            const errEl = this.$('pylance-errors');
            const warnEl = this.$('pylance-warnings');
            const filesEl = this.$('pylance-files');
            const verEl = this.$('pylance-version');
            
            if (errEl) errEl.textContent = this.data.total_errors || 0;
            if (warnEl) warnEl.textContent = this.data.total_warnings || 0;
            if (filesEl) filesEl.textContent = this.data.files_with_errors || 0;
            if (verEl) verEl.textContent = this.data.pyright_version || '—';
            
            this.hideAllStatus();
            
            if (this.data.total_errors === 0 && this.data.total_warnings === 0) {
                this.showAllGood();
            } else {
                const filesSection = this.$('pylance-files-section');
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
            if (!this.data?.file_reports) return;
            
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
        },
        
        shortenPath(path) {
            const parts = path.replace(/\\\\/g, '/').split('/');
            return parts.length <= 3 ? path : '.../' + parts.slice(-3).join('/');
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
                return text + '✅ No type errors or warnings found!\\n';
            }
            
            text += '## Issues by File\\n\\n';
            const filesToExport = filePathFilter 
                ? this.data.file_reports.filter(f => f.path === filePathFilter)
                : this.data.file_reports;
            
            for (const file of filesToExport) {
                if (file.error_count === 0 && file.warning_count === 0) continue;
                text += `### ${file.path}\\n\\n`;
                for (const diag of file.diagnostics) {
                    const icon = diag.severity === 'error' ? '🔴' : diag.severity === 'warning' ? '🟡' : '🔵';
                    text += `${icon} **Line ${diag.line}:${diag.column}** [${diag.severity}]`;
                    if (diag.rule) text += ` (${diag.rule})`;
                    text += `\\n   ${diag.message}\\n\\n`;
                }
            }
            
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
                    const orig = copyBtn.innerHTML;
                    copyBtn.innerHTML = '✅ Copied!';
                    setTimeout(() => { copyBtn.innerHTML = orig; }, 2000);
                }
            } catch (err) {
                content.select();
                document.execCommand('copy');
            }
        },
        
        bindEvents() {
            this.$('pylance-refresh-btn')?.addEventListener('click', () => this.loadData());
            this.$('pylance-export-btn')?.addEventListener('click', () => this.showExportModal());
            this.$('pylance-export-file-btn')?.addEventListener('click', () => {
                if (this.currentFilePath) this.showExportModal(this.currentFilePath);
            });
            this.$('pylance-copy-btn')?.addEventListener('click', () => this.copyToClipboard());
            document.querySelectorAll('[data-action="close-pylance-export"]').forEach(btn => {
                btn.addEventListener('click', () => this.closeExportModal());
            });
            this.$('pylance-filter')?.addEventListener('input', () => this.renderFilesTable());
            this.$('pylance-severity-filter')?.addEventListener('change', () => this.renderFilesTable());
            this.$('pylance-files-body')?.addEventListener('click', (e) => {
                if (e.target.matches('button[data-path]')) {
                    this.showFileDetails(e.target.dataset.path);
                }
            });
            this.$('pylance-back-btn')?.addEventListener('click', () => this.hideFileDetails());
        }
    };
    
    window.pylanceView = controller;
    window.pylance_analyzerView = controller;
})();
"""


# =============================================================================
# SETTINGS HTML/JS
# =============================================================================

_SETTINGS_HTML = """
<div class="settings-card" id="pylance-settings">
    <h3>🔍 Pylance Analyzer</h3>
    <div class="settings-form">
        <label class="setting-row">
            <span>Enable Analysis</span>
            <input type="checkbox" id="pylance-enabled" checked>
        </label>
        <label class="setting-row">
            <span>Strict Mode</span>
            <input type="checkbox" id="pylance-strict">
        </label>
        <label class="setting-row">
            <span>Include Warnings</span>
            <input type="checkbox" id="pylance-include-warnings" checked>
        </label>
        <label class="setting-row">
            <span>Include Info</span>
            <input type="checkbox" id="pylance-include-info">
        </label>
        <label class="setting-row">
            <span>Max Files</span>
            <input type="number" id="pylance-max-files" value="500" min="1" max="10000">
        </label>
        <label class="setting-row">
            <span>Timeout (seconds)</span>
            <input type="number" id="pylance-timeout" value="120" min="10" max="600">
        </label>
        <button class="btn btn-primary" id="pylance-save-settings">Save</button>
    </div>
</div>
"""

_SETTINGS_JS = """
(function() {
    const settingsCtrl = {
        async loadSettings() {
            try {
                const apiBase = (typeof state !== 'undefined' && state.apiBaseUrl) 
                    ? state.apiBaseUrl 
                    : window.location.protocol + '//' + window.location.hostname + ':8000';
                const resp = await fetch(`${apiBase}/plugins/pylance_analyzer/config`);
                if (resp.ok) {
                    const config = await resp.json();
                    document.getElementById('pylance-enabled').checked = config.enabled !== false;
                    document.getElementById('pylance-strict').checked = !!config.strict;
                    document.getElementById('pylance-include-warnings').checked = config.include_warnings !== false;
                    document.getElementById('pylance-include-info').checked = !!config.include_info;
                    document.getElementById('pylance-max-files').value = config.max_files || 500;
                    document.getElementById('pylance-timeout').value = config.timeout || 120;
                }
            } catch (err) {
                console.error('[Pylance Settings] Load error:', err);
            }
        },
        
        async saveSettings() {
            const config = {
                enabled: document.getElementById('pylance-enabled').checked,
                strict: document.getElementById('pylance-strict').checked,
                include_warnings: document.getElementById('pylance-include-warnings').checked,
                include_info: document.getElementById('pylance-include-info').checked,
                max_files: parseInt(document.getElementById('pylance-max-files').value) || 500,
                timeout: parseInt(document.getElementById('pylance-timeout').value) || 120
            };
            
            try {
                const apiBase = (typeof state !== 'undefined' && state.apiBaseUrl) 
                    ? state.apiBaseUrl 
                    : window.location.protocol + '//' + window.location.hostname + ':8000';
                const resp = await fetch(`${apiBase}/plugins/pylance_analyzer/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                if (resp.ok) {
                    alert('Settings saved!');
                }
            } catch (err) {
                console.error('[Pylance Settings] Save error:', err);
            }
        },
        
        init() {
            this.loadSettings();
            document.getElementById('pylance-save-settings')?.addEventListener('click', () => this.saveSettings());
        }
    };
    
    window.pylanceSettingsCtrl = settingsCtrl;
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => settingsCtrl.init());
    } else {
        settingsCtrl.init();
    }
})();
"""
