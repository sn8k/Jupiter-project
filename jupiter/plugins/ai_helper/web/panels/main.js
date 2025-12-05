/**
 * web/panels/main.js – AI Helper main panel for WebUI.
 * Version: 1.3.0
 *
 * This file is dynamically loaded by the plugin receptacle.
 * Exports mount(container, bridge) called by the WebUI.
 * 
 * Conforme à plugins_architecture.md v0.4.0
 */

// Inline CSS for the AI Helper plugin
const AI_HELPER_CSS = `
/* AI Helper Plugin Styles v1.3.0 */
.ai-helper-plugin { display: flex; flex-direction: column; height: 100%; color: var(--text); font-family: var(--font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif); }
.ai-helper-plugin .plugin-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--panel-contrast, #1a1a2e); }
.ai-helper-plugin .plugin-header h2 { margin: 0; font-size: 18px; font-weight: 600; color: var(--text); }
.ai-helper-plugin .plugin-version { font-size: 12px; color: var(--text-muted); background: var(--background); padding: 2px 8px; border-radius: 4px; }
.ai-helper-plugin .plugin-body { flex: 1; display: flex; gap: 20px; padding: 20px; overflow-y: auto; }
.ai-helper-plugin .plugin-main { flex: 1; display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.ai-helper-plugin .plugin-help { width: 280px; flex-shrink: 0; padding: 16px; background: var(--panel-contrast, #1a1a2e); border-radius: 8px; border: 1px solid var(--border); font-size: 13px; line-height: 1.6; }
.ai-helper-plugin .plugin-help h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--primary); }
.ai-helper-plugin .plugin-help h4 { margin: 16px 0 8px 0; font-size: 13px; color: var(--text); }
.ai-helper-plugin .plugin-help p { margin: 0 0 12px 0; color: var(--text-muted); }
.ai-helper-plugin .plugin-help ul { margin: 0; padding-left: 16px; }
.ai-helper-plugin .plugin-help li { margin-bottom: 6px; color: var(--text-muted); }
.ai-helper-plugin .plugin-help a { color: var(--primary); text-decoration: none; }
.ai-helper-plugin .plugin-help a:hover { text-decoration: underline; }
.ai-helper-plugin section { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.ai-helper-plugin section h3 { margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: var(--text); }
.ai-helper-plugin .control-section { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.ai-helper-plugin .control-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
.ai-helper-plugin .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; border: none; border-radius: 6px; cursor: pointer; transition: all 0.2s ease; }
.ai-helper-plugin .btn-primary { background: var(--primary); color: white; }
.ai-helper-plugin .btn-primary:hover:not(:disabled) { background: var(--primary-hover, #5a7fff); transform: translateY(-1px); }
.ai-helper-plugin .btn-secondary { background: var(--panel-contrast, #252540); color: var(--text); border: 1px solid var(--border); }
.ai-helper-plugin .btn-secondary:hover:not(:disabled) { background: var(--background-hover, #2a2a45); }
.ai-helper-plugin .btn:disabled { opacity: 0.5; cursor: not-allowed; }
.ai-helper-plugin .btn-sm { padding: 6px 12px; font-size: 12px; }
.ai-helper-plugin .btn-icon { font-size: 14px; }
.ai-helper-plugin .status-indicator { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; background: var(--panel-contrast, #1a1a2e); border-radius: 20px; font-size: 12px; max-width: 100%; overflow: hidden; flex-shrink: 0; }
.ai-helper-plugin .status-dot { width: 8px; height: 8px; min-width: 8px; border-radius: 50%; background: var(--text-muted); flex-shrink: 0; }
.ai-helper-plugin .status-dot.status-success { background: var(--success, #4caf50); box-shadow: 0 0 6px var(--success, #4caf50); }
.ai-helper-plugin .status-dot.status-running { background: var(--primary); animation: ai-pulse 1.5s infinite; }
.ai-helper-plugin .status-dot.status-error { background: var(--danger, #f44336); }
.ai-helper-plugin .status-dot.status-warning { background: var(--warning, #ff9800); }
@keyframes ai-pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(1.1); } }
.ai-helper-plugin .status-text { color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ai-helper-plugin .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
.ai-helper-plugin .info-item { display: flex; flex-direction: column; gap: 4px; }
.ai-helper-plugin .info-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.ai-helper-plugin .info-value { font-size: 14px; font-weight: 500; color: var(--text); }
.ai-helper-plugin .filter-controls { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.ai-helper-plugin .filter-select { padding: 6px 10px; font-size: 12px; background: var(--panel-contrast, #1a1a2e); color: var(--text); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; }
.ai-helper-plugin .filter-select:focus { outline: none; border-color: var(--primary); }
.ai-helper-plugin .suggestions-list { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
.ai-helper-plugin .empty-state { color: var(--text-muted); font-style: italic; text-align: center; padding: 20px; }
.ai-helper-plugin .suggestion-item { padding: 12px; background: var(--panel-contrast, #1a1a2e); border-radius: 6px; border-left: 3px solid var(--text-muted); }
.ai-helper-plugin .suggestion-item.severity-info { border-left-color: var(--info, #2196f3); }
.ai-helper-plugin .suggestion-item.severity-low { border-left-color: var(--success, #4caf50); }
.ai-helper-plugin .suggestion-item.severity-medium { border-left-color: var(--warning, #ff9800); }
.ai-helper-plugin .suggestion-item.severity-high { border-left-color: var(--danger, #f44336); }
.ai-helper-plugin .suggestion-item.severity-critical { border-left-color: #9c27b0; background: rgba(156, 39, 176, 0.1); }
.ai-helper-plugin .suggestion-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.ai-helper-plugin .suggestion-type { font-size: 11px; text-transform: uppercase; color: var(--primary); font-weight: 600; }
.ai-helper-plugin .suggestion-severity { font-size: 10px; padding: 2px 6px; border-radius: 3px; background: var(--background); color: var(--text-muted); }
.ai-helper-plugin .suggestion-path { font-size: 12px; color: var(--text-muted); font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace); margin-bottom: 6px; word-break: break-all; }
.ai-helper-plugin .suggestion-details { font-size: 13px; color: var(--text); line-height: 1.5; }
.ai-helper-plugin .export-actions { display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
.ai-helper-plugin .logs-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.ai-helper-plugin .logs-header h3 { margin: 0; }
.ai-helper-plugin .logs-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.ai-helper-plugin .logs-controls select, .ai-helper-plugin .logs-controls input { padding: 5px 8px; font-size: 12px; background: var(--panel-contrast, #1a1a2e); color: var(--text); border: 1px solid var(--border); border-radius: 4px; }
.ai-helper-plugin .logs-controls input { width: 150px; }
.ai-helper-plugin .logs-controls input:focus, .ai-helper-plugin .logs-controls select:focus { outline: none; border-color: var(--primary); }
.ai-helper-plugin .logs-stream { height: 200px; overflow-y: auto; padding: 12px; background: var(--background, #0d0d1a); border-radius: 6px; font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace); font-size: 11px; line-height: 1.6; color: var(--text-muted); white-space: pre-wrap; word-break: break-all; margin: 0; }
.ai-helper-plugin .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; }
.ai-helper-plugin .stat-item { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 12px; background: var(--panel-contrast, #1a1a2e); border-radius: 8px; }
.ai-helper-plugin .stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.ai-helper-plugin .stat-value { font-size: 20px; font-weight: 700; color: var(--primary); }
@media (max-width: 900px) { .ai-helper-plugin .plugin-body { flex-direction: column; } .ai-helper-plugin .plugin-help { width: 100%; } }
@media (max-width: 600px) { .ai-helper-plugin .control-section { flex-direction: column; align-items: stretch; } .ai-helper-plugin .control-buttons { justify-content: center; } .ai-helper-plugin .status-indicator { justify-content: center; width: 100%; } }
`;

// Inject CSS if not already loaded
const AI_HELPER_CSS_ID = 'ai-helper-plugin-styles';
if (!document.getElementById(AI_HELPER_CSS_ID)) {
  const style = document.createElement('style');
  style.id = AI_HELPER_CSS_ID;
  style.textContent = AI_HELPER_CSS;
  document.head.appendChild(style);
}

export function mount(container, bridge) {
  // Get i18n translation function
  const t = bridge.i18n.t;

  // Panel structure
  container.innerHTML = `
    <div class="plugin-panel ai-helper-plugin">
      <header class="plugin-header">
        <h2>${t('ai_helper_title')}</h2>
        <span class="plugin-version">v1.1.0</span>
      </header>
      
      <div class="plugin-body">
        <div class="plugin-main">
          <!-- Control Section -->
          <section class="control-section">
            <div class="control-buttons">
              <button id="ai-run-analysis" class="btn btn-primary">
                <span class="btn-icon">🤖</span>
                ${t('ai_helper_run_analysis')}
              </button>
              <button id="ai-refresh-suggestions" class="btn btn-secondary">
                <span class="btn-icon">🔄</span>
                ${t('ai_helper_refresh')}
              </button>
            </div>
            <div id="ai-status" class="status-indicator">
              <span class="status-dot"></span>
              <span class="status-text">${t('ai_helper_status_idle')}</span>
            </div>
          </section>

          <!-- Provider Info -->
          <section class="info-section">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">${t('ai_helper_provider')}</span>
                <span id="ai-provider" class="info-value">-</span>
              </div>
              <div class="info-item">
                <span class="info-label">${t('ai_helper_enabled')}</span>
                <span id="ai-enabled" class="info-value">-</span>
              </div>
            </div>
          </section>

          <!-- Suggestions Results -->
          <section class="results-section">
            <h3>${t('ai_helper_suggestions_title')}</h3>
            <div class="filter-controls">
              <select id="ai-filter-type" class="filter-select">
                <option value="all">${t('ai_helper_filter_all')}</option>
                <option value="refactoring">${t('ai_helper_filter_refactoring')}</option>
                <option value="doc">${t('ai_helper_filter_doc')}</option>
                <option value="security">${t('ai_helper_filter_security')}</option>
                <option value="optimization">${t('ai_helper_filter_optimization')}</option>
                <option value="testing">${t('ai_helper_filter_testing')}</option>
                <option value="cleanup">${t('ai_helper_filter_cleanup')}</option>
              </select>
              <select id="ai-filter-severity" class="filter-select">
                <option value="info">INFO+</option>
                <option value="low">LOW+</option>
                <option value="medium">MEDIUM+</option>
                <option value="high">HIGH+</option>
                <option value="critical">CRITICAL</option>
              </select>
            </div>
            <div id="ai-suggestions-list" class="suggestions-list">
              <p class="empty-state">${t('ai_helper_no_suggestions')}</p>
            </div>
            
            <!-- Export Actions -->
            <div class="export-actions">
              <button id="ai-export-json" class="btn btn-secondary btn-sm">
                ${t('ai_helper_export_json')}
              </button>
              <button id="ai-export-ai" class="btn btn-secondary btn-sm">
                ${t('ai_helper_export_ai_context')}
              </button>
            </div>
          </section>

          <!-- Real-time Logs Panel -->
          <section class="logs-section">
            <div class="logs-header">
              <h3>${t('ai_helper_logs_title')}</h3>
              <div class="logs-controls">
                <select id="ai-log-level">
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO" selected>INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
                <input type="text" id="ai-log-search" placeholder="${t('ai_helper_logs_search')}" />
                <button id="ai-logs-pause" class="btn btn-sm btn-secondary">
                  ${t('ai_helper_logs_pause')}
                </button>
                <button id="ai-logs-download" class="btn btn-sm btn-secondary">
                  ${t('ai_helper_logs_download')}
                </button>
              </div>
            </div>
            <pre id="ai-logs-output" class="logs-stream"></pre>
          </section>

          <!-- Usage Statistics -->
          <section class="stats-section">
            <h3>${t('ai_helper_stats_title')}</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">${t('ai_helper_stats_executions')}</span>
                <span id="ai-stat-executions" class="stat-value">0</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('ai_helper_stats_total_suggestions')}</span>
                <span id="ai-stat-total" class="stat-value">0</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('ai_helper_stats_last_run')}</span>
                <span id="ai-stat-last-run" class="stat-value">-</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('ai_helper_stats_errors')}</span>
                <span id="ai-stat-errors" class="stat-value">0</span>
              </div>
            </div>
          </section>
        </div>

        <!-- Help Sidebar -->
        <aside class="plugin-help">
          <h3>${t('ai_helper_help_title')}</h3>
          <p>${t('ai_helper_help_description')}</p>
          <h4>${t('ai_helper_help_types')}</h4>
          <ul>
            <li><strong>refactoring</strong>: ${t('ai_helper_type_refactoring')}</li>
            <li><strong>doc</strong>: ${t('ai_helper_type_doc')}</li>
            <li><strong>security</strong>: ${t('ai_helper_type_security')}</li>
            <li><strong>optimization</strong>: ${t('ai_helper_type_optimization')}</li>
            <li><strong>testing</strong>: ${t('ai_helper_type_testing')}</li>
            <li><strong>cleanup</strong>: ${t('ai_helper_type_cleanup')}</li>
          </ul>
          <a href="/docs/plugins/ai_helper" target="_blank">${t('ai_helper_help_link')}</a>
        </aside>
      </div>
    </div>
  `;

  // === DOM References ===
  const runBtn = container.querySelector('#ai-run-analysis');
  const refreshBtn = container.querySelector('#ai-refresh-suggestions');
  const statusText = container.querySelector('.status-text');
  const statusDot = container.querySelector('.status-dot');
  const providerSpan = container.querySelector('#ai-provider');
  const enabledSpan = container.querySelector('#ai-enabled');
  const suggestionsList = container.querySelector('#ai-suggestions-list');
  const filterType = container.querySelector('#ai-filter-type');
  const filterSeverity = container.querySelector('#ai-filter-severity');
  const exportJsonBtn = container.querySelector('#ai-export-json');
  const exportAiBtn = container.querySelector('#ai-export-ai');
  const logsOutput = container.querySelector('#ai-logs-output');
  const logLevelSelect = container.querySelector('#ai-log-level');
  const logSearchInput = container.querySelector('#ai-log-search');
  const pauseBtn = container.querySelector('#ai-logs-pause');
  const downloadLogsBtn = container.querySelector('#ai-logs-download');

  let currentSuggestions = [];
  let logsPaused = false;
  let logsBuffer = [];
  let ws = null;

  // === Helper Functions ===
  
  function setStatus(status, text) {
    statusText.textContent = text;
    statusDot.className = 'status-dot status-' + status;
  }

  function renderSuggestions(suggestions) {
    if (!suggestions || suggestions.length === 0) {
      suggestionsList.innerHTML = `<p class="empty-state">${t('ai_helper_no_suggestions')}</p>`;
      return;
    }

    // Apply filters
    const typeFilter = filterType.value;
    const sevFilter = filterSeverity.value;
    const severityOrder = ['info', 'low', 'medium', 'high', 'critical'];
    const sevIdx = severityOrder.indexOf(sevFilter);

    const filtered = suggestions.filter(s => {
      const typeMatch = typeFilter === 'all' || s.type === typeFilter;
      const sIdx = severityOrder.indexOf(s.severity || 'info');
      const sevMatch = sIdx >= sevIdx;
      return typeMatch && sevMatch;
    });

    if (filtered.length === 0) {
      suggestionsList.innerHTML = `<p class="empty-state">${t('ai_helper_no_matching')}</p>`;
      return;
    }

    const html = filtered.map((s, i) => `
      <div class="suggestion-item severity-${s.severity || 'info'}">
        <div class="suggestion-header">
          <span class="suggestion-type">${s.type}</span>
          <span class="suggestion-severity">${(s.severity || 'info').toUpperCase()}</span>
        </div>
        <div class="suggestion-path">${s.path}</div>
        <div class="suggestion-details">${s.details}</div>
      </div>
    `).join('');

    suggestionsList.innerHTML = html;
  }

  // === Event Handlers ===

  runBtn.addEventListener('click', async () => {
    setStatus('running', t('ai_helper_status_running'));
    runBtn.disabled = true;
    
    try {
      // Trigger full analysis via API
      const res = await bridge.api.post('/analyze');
      // Then fetch suggestions
      const suggestions = await bridge.api.get('/ai_helper/suggestions');
      currentSuggestions = suggestions;
      renderSuggestions(currentSuggestions);
      setStatus('success', t('ai_helper_status_done'));
      loadStats();
    } catch (err) {
      console.error('AI analysis failed:', err);
      setStatus('error', t('ai_helper_status_error'));
    } finally {
      runBtn.disabled = false;
    }
  });

  refreshBtn.addEventListener('click', async () => {
    try {
      const suggestions = await bridge.api.get('/ai_helper/suggestions');
      currentSuggestions = suggestions;
      renderSuggestions(currentSuggestions);
    } catch (err) {
      console.error('Failed to refresh suggestions:', err);
    }
  });

  filterType.addEventListener('change', () => renderSuggestions(currentSuggestions));
  filterSeverity.addEventListener('change', () => renderSuggestions(currentSuggestions));

  exportJsonBtn.addEventListener('click', () => {
    if (!currentSuggestions || currentSuggestions.length === 0) return;
    const blob = new Blob([JSON.stringify(currentSuggestions, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'ai_suggestions.json';
    a.click();
    URL.revokeObjectURL(url);
  });

  exportAiBtn.addEventListener('click', async () => {
    if (!currentSuggestions || currentSuggestions.length === 0) return;
    await bridge.ai.sendContext('ai_helper', currentSuggestions);
    bridge.notify.info(t('ai_helper_export_done'));
  });

  // === Logs Handling ===

  function connectLogsStream() {
    try {
      ws = bridge.ws.connect('/ai_helper/logs/stream');
      ws.onmessage = (event) => {
        if (logsPaused) return;
        
        const levelFilter = logLevelSelect.value;
        const searchFilter = logSearchInput.value.toLowerCase();
        const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];
        
        // Parse SSE data
        let logLine = event.data;
        if (logLine.startsWith('data: ')) {
          logLine = logLine.substring(6);
        }

        // Simple level detection
        const levelMatch = logLine.match(/\[(DEBUG|INFO|WARNING|ERROR)\]/i);
        const logLevel = levelMatch ? levelMatch[1].toUpperCase() : 'INFO';

        // Level filter
        if (levels.indexOf(logLevel) < levels.indexOf(levelFilter)) return;

        // Search filter
        if (searchFilter && !logLine.toLowerCase().includes(searchFilter)) return;

        logsBuffer.push(logLine);
        if (logsBuffer.length > 500) logsBuffer.shift();

        logsOutput.textContent += logLine + '\n';
        logsOutput.scrollTop = logsOutput.scrollHeight;
      };
    } catch (err) {
      console.error('Failed to connect log stream:', err);
    }
  }

  pauseBtn.addEventListener('click', () => {
    logsPaused = !logsPaused;
    pauseBtn.textContent = logsPaused ? t('ai_helper_logs_resume') : t('ai_helper_logs_pause');
  });

  downloadLogsBtn.addEventListener('click', async () => {
    try {
      const response = await bridge.api.get('/ai_helper/logs', { responseType: 'text' });
      const blob = new Blob([response], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ai_helper.log';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download logs:', err);
    }
  });

  // === Statistics ===

  async function loadStats() {
    try {
      const metrics = await bridge.api.get('/ai_helper/metrics');
      container.querySelector('#ai-stat-executions').textContent = metrics.ai_helper_executions_total || 0;
      container.querySelector('#ai-stat-total').textContent = metrics.ai_helper_suggestions_total || 0;
      container.querySelector('#ai-stat-last-run').textContent = metrics.ai_helper_last_execution || '-';
      container.querySelector('#ai-stat-errors').textContent = metrics.ai_helper_errors_total || 0;
      
      // Update provider info
      providerSpan.textContent = metrics.ai_helper_provider || 'mock';
      enabledSpan.textContent = metrics.ai_helper_enabled ? '✓' : '✗';
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }

  async function loadHealth() {
    try {
      const health = await bridge.api.get('/ai_helper/health');
      const status = health.status || 'unknown';
      setStatus(status === 'healthy' ? 'success' : 'warning', 
                status === 'healthy' ? t('ai_helper_status_healthy') : health.message);
    } catch (err) {
      setStatus('error', t('ai_helper_status_unavailable'));
    }
  }

  // === Initial Load ===
  loadHealth();
  loadStats();
  refreshBtn.click(); // Load initial suggestions
  connectLogsStream();
}

export function unmount(container) {
  // Cleanup
  container.innerHTML = '';
}
