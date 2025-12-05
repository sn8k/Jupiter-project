"""
Code Quality plugin - Web UI templates.

Version: 0.8.1

Provides HTML/CSS/JS templates for the Code Quality analysis view
and settings panel.
"""


def get_ui_html() -> str:
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
"""


def get_ui_css() -> str:
    """Return CSS styles for the Code Quality view."""
    return """
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


def get_ui_js() -> str:
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


def get_settings_html() -> str:
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
"""


def get_settings_css() -> str:
    """Return CSS for the settings section."""
    return """
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


def get_settings_js() -> str:
    """Return JavaScript for the settings section."""
    return """
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
"""
