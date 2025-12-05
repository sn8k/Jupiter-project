/**
 * web/panels/main.js – Metrics Manager main panel for WebUI.
 * Version: 1.0.4 - Plugin metrics null guards and base URL inference for logs
 *
 * This file is dynamically loaded by the plugin receptacle.
 * Exports mount(container, bridge) called by the WebUI.
 * 
 * Conforme à plugins_architecture.md v0.6.0
 */

// Inline CSS for the Metrics Manager plugin
const METRICS_MANAGER_CSS = `
/* Metrics Manager Plugin Styles v1.0.0 */
.metrics-manager-plugin { display: flex; flex-direction: column; height: 100%; color: var(--text); font-family: var(--font-family, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif); }
.metrics-manager-plugin .plugin-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); background: var(--panel-contrast, #1a1a2e); }
.metrics-manager-plugin .plugin-header h2 { margin: 0; font-size: 18px; font-weight: 600; color: var(--text); }
.metrics-manager-plugin .plugin-version { font-size: 12px; color: var(--text-muted); background: var(--background); padding: 2px 8px; border-radius: 4px; }
.metrics-manager-plugin .plugin-body { flex: 1; display: flex; gap: 20px; padding: 20px; overflow-y: auto; }
.metrics-manager-plugin .plugin-main { flex: 1; display: flex; flex-direction: column; gap: 20px; min-width: 0; }
.metrics-manager-plugin .plugin-sidebar { width: 280px; flex-shrink: 0; display: flex; flex-direction: column; gap: 16px; }
.metrics-manager-plugin .plugin-help { padding: 16px; background: var(--panel-contrast, #1a1a2e); border-radius: 8px; border: 1px solid var(--border); font-size: 13px; line-height: 1.6; }
.metrics-manager-plugin .plugin-help h3 { margin: 0 0 12px 0; font-size: 14px; color: var(--primary); }
.metrics-manager-plugin .plugin-help p { margin: 0 0 12px 0; color: var(--text-muted); }
.metrics-manager-plugin .plugin-help ul { margin: 0; padding-left: 16px; }
.metrics-manager-plugin .plugin-help li { margin-bottom: 6px; color: var(--text-muted); }
.metrics-manager-plugin .plugin-help a { color: var(--primary); text-decoration: none; }
.metrics-manager-plugin .plugin-help a:hover { text-decoration: underline; }
.metrics-manager-plugin section { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
.metrics-manager-plugin section h3 { margin: 0 0 12px 0; font-size: 14px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 8px; }
.metrics-manager-plugin section h3 .icon { font-size: 16px; }
.metrics-manager-plugin .control-section { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.metrics-manager-plugin .control-buttons { display: flex; gap: 10px; flex-wrap: wrap; }
.metrics-manager-plugin .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; font-size: 13px; font-weight: 500; border: none; border-radius: 6px; cursor: pointer; transition: all 0.2s ease; }
.metrics-manager-plugin .btn-primary { background: var(--primary); color: white; }
.metrics-manager-plugin .btn-primary:hover:not(:disabled) { background: var(--primary-hover, #5a7fff); transform: translateY(-1px); }
.metrics-manager-plugin .btn-secondary { background: var(--panel-contrast, #252540); color: var(--text); border: 1px solid var(--border); }
.metrics-manager-plugin .btn-secondary:hover:not(:disabled) { background: var(--background-hover, #2a2a45); }
.metrics-manager-plugin .btn-danger { background: var(--danger, #dc3545); color: white; }
.metrics-manager-plugin .btn-danger:hover:not(:disabled) { background: #c82333; }
.metrics-manager-plugin .btn:disabled { opacity: 0.5; cursor: not-allowed; }
.metrics-manager-plugin .btn-sm { padding: 6px 12px; font-size: 12px; }
.metrics-manager-plugin .btn-icon { font-size: 14px; }
.metrics-manager-plugin .status-indicator { display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px; background: var(--panel-contrast, #1a1a2e); border-radius: 20px; font-size: 12px; }
.metrics-manager-plugin .status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.metrics-manager-plugin .status-dot.status-success { background: var(--success, #4caf50); box-shadow: 0 0 6px var(--success, #4caf50); }
.metrics-manager-plugin .status-dot.status-running { background: var(--primary); animation: metrics-pulse 1.5s infinite; }
.metrics-manager-plugin .status-dot.status-error { background: var(--danger, #f44336); }
.metrics-manager-plugin .status-dot.status-warning { background: var(--warning, #ff9800); }
@keyframes metrics-pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(1.1); } }
.metrics-manager-plugin .status-text { color: var(--text-muted); }

/* System Metrics Grid */
.metrics-manager-plugin .system-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
.metrics-manager-plugin .metric-card { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 16px; background: var(--panel-contrast, #1a1a2e); border-radius: 8px; transition: transform 0.2s ease; }
.metrics-manager-plugin .metric-card:hover { transform: translateY(-2px); }
.metrics-manager-plugin .metric-icon { font-size: 24px; margin-bottom: 8px; }
.metrics-manager-plugin .metric-value { font-size: 24px; font-weight: 700; color: var(--primary); margin-bottom: 4px; }
.metrics-manager-plugin .metric-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

/* Counters & Gauges Tables */
.metrics-manager-plugin .metrics-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.metrics-manager-plugin .metrics-table th { text-align: left; padding: 10px 12px; background: var(--panel-contrast, #1a1a2e); color: var(--text-muted); font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid var(--border); }
.metrics-manager-plugin .metrics-table td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
.metrics-manager-plugin .metrics-table tr:hover td { background: rgba(255, 255, 255, 0.02); }
.metrics-manager-plugin .metrics-table .metric-name { font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace); color: var(--primary); }
.metrics-manager-plugin .metrics-table .metric-value { font-weight: 600; text-align: right; }
.metrics-manager-plugin .metrics-table .metric-type { color: var(--text-muted); font-size: 11px; }
.metrics-manager-plugin .metrics-table .empty-row td { color: var(--text-muted); font-style: italic; text-align: center; }

/* Alerts Section */
.metrics-manager-plugin .alerts-list { display: flex; flex-direction: column; gap: 8px; max-height: 200px; overflow-y: auto; }
.metrics-manager-plugin .alert-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: var(--panel-contrast, #1a1a2e); border-radius: 6px; border-left: 3px solid var(--text-muted); }
.metrics-manager-plugin .alert-item.severity-warning { border-left-color: var(--warning, #ff9800); background: rgba(255, 152, 0, 0.1); }
.metrics-manager-plugin .alert-item.severity-critical { border-left-color: var(--danger, #f44336); background: rgba(244, 67, 54, 0.1); }
.metrics-manager-plugin .alert-item.severity-info { border-left-color: var(--info, #2196f3); }
.metrics-manager-plugin .alert-icon { font-size: 18px; }
.metrics-manager-plugin .alert-content { flex: 1; }
.metrics-manager-plugin .alert-message { font-size: 13px; color: var(--text); margin-bottom: 4px; }
.metrics-manager-plugin .alert-details { font-size: 11px; color: var(--text-muted); }
.metrics-manager-plugin .empty-state { color: var(--text-muted); font-style: italic; text-align: center; padding: 20px; }

/* Plugin Metrics Accordion */
.metrics-manager-plugin .plugin-metrics-list { display: flex; flex-direction: column; gap: 8px; }
.metrics-manager-plugin .plugin-metrics-item { background: var(--panel-contrast, #1a1a2e); border-radius: 6px; overflow: hidden; }
.metrics-manager-plugin .plugin-metrics-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; cursor: pointer; transition: background 0.2s ease; }
.metrics-manager-plugin .plugin-metrics-header:hover { background: rgba(255, 255, 255, 0.03); }
.metrics-manager-plugin .plugin-metrics-name { font-weight: 500; display: flex; align-items: center; gap: 8px; }
.metrics-manager-plugin .plugin-metrics-name .chevron { transition: transform 0.2s ease; }
.metrics-manager-plugin .plugin-metrics-item.expanded .chevron { transform: rotate(90deg); }
.metrics-manager-plugin .plugin-metrics-body { padding: 0 16px 16px 16px; display: none; }
.metrics-manager-plugin .plugin-metrics-item.expanded .plugin-metrics-body { display: block; }

/* Chart Container */
.metrics-manager-plugin .chart-container { height: 200px; background: var(--panel-contrast, #1a1a2e); border-radius: 6px; padding: 16px; display: flex; flex-direction: column; }
.metrics-manager-plugin .chart-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.metrics-manager-plugin .chart-title { font-size: 13px; font-weight: 500; }
.metrics-manager-plugin .chart-controls { display: flex; gap: 8px; }
.metrics-manager-plugin .chart-area { flex: 1; position: relative; }
.metrics-manager-plugin .chart-canvas { width: 100%; height: 100%; }
.metrics-manager-plugin .chart-placeholder { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-style: italic; }

/* Metric History Select */
.metrics-manager-plugin .history-select { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
.metrics-manager-plugin .history-select select { padding: 6px 10px; font-size: 12px; background: var(--panel-contrast, #1a1a2e); color: var(--text); border: 1px solid var(--border); border-radius: 4px; cursor: pointer; min-width: 200px; }
.metrics-manager-plugin .history-select select:focus { outline: none; border-color: var(--primary); }

/* Logs Section */
.metrics-manager-plugin .logs-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 12px; }
.metrics-manager-plugin .logs-header h3 { margin: 0; }
.metrics-manager-plugin .logs-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.metrics-manager-plugin .logs-controls select, .metrics-manager-plugin .logs-controls input { padding: 5px 8px; font-size: 12px; background: var(--panel-contrast, #1a1a2e); color: var(--text); border: 1px solid var(--border); border-radius: 4px; }
.metrics-manager-plugin .logs-controls input { width: 150px; }
.metrics-manager-plugin .logs-stream { height: 150px; overflow-y: auto; padding: 12px; background: var(--background, #0d0d1a); border-radius: 6px; font-family: var(--font-mono, 'SF Mono', 'Consolas', monospace); font-size: 11px; line-height: 1.6; color: var(--text-muted); white-space: pre-wrap; word-break: break-all; }

/* Stats Grid */
.metrics-manager-plugin .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 12px; }
.metrics-manager-plugin .stat-item { display: flex; flex-direction: column; align-items: center; text-align: center; padding: 12px; background: var(--panel-contrast, #1a1a2e); border-radius: 6px; }
.metrics-manager-plugin .stat-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.metrics-manager-plugin .stat-value { font-size: 18px; font-weight: 700; color: var(--primary); }

/* Responsive */
@media (max-width: 1100px) { .metrics-manager-plugin .plugin-body { flex-direction: column; } .metrics-manager-plugin .plugin-sidebar { width: 100%; flex-direction: row; flex-wrap: wrap; } .metrics-manager-plugin .plugin-sidebar > * { flex: 1; min-width: 250px; } }
@media (max-width: 600px) { .metrics-manager-plugin .control-section { flex-direction: column; align-items: stretch; } .metrics-manager-plugin .control-buttons { justify-content: center; } .metrics-manager-plugin .system-grid { grid-template-columns: repeat(2, 1fr); } }
`;

// Inject CSS if not already loaded
const METRICS_MANAGER_CSS_ID = 'metrics-manager-plugin-styles';
if (!document.getElementById(METRICS_MANAGER_CSS_ID)) {
  const style = document.createElement('style');
  style.id = METRICS_MANAGER_CSS_ID;
  style.textContent = METRICS_MANAGER_CSS;
  document.head.appendChild(style);
}

// Plugin state
let refreshInterval = null;
let logsEventSource = null;
let logsPaused = false;
let allMetrics = null;

export function mount(container, bridge) {
  // Get i18n translation function
  const t = bridge.i18n.t;

  // Panel structure
  container.innerHTML = `
    <div class="plugin-panel metrics-manager-plugin">
      <header class="plugin-header">
        <h2>📊 ${t('metrics_manager_title')}</h2>
        <span class="plugin-version">v1.0.4</span>
      </header>
      
      <div class="plugin-body">
        <div class="plugin-main">
          <!-- Control Section -->
          <section class="control-section">
            <div class="control-buttons">
              <button id="mm-refresh" class="btn btn-primary">
                <span class="btn-icon">🔄</span>
                ${t('metrics_manager_refresh')}
              </button>
              <button id="mm-export-json" class="btn btn-secondary">
                <span class="btn-icon">📥</span>
                ${t('metrics_manager_export_json')}
              </button>
              <button id="mm-export-prometheus" class="btn btn-secondary">
                <span class="btn-icon">📊</span>
                ${t('metrics_manager_export_prometheus')}
              </button>
              <button id="mm-reset" class="btn btn-danger btn-sm">
                <span class="btn-icon">🗑️</span>
                ${t('metrics_manager_reset')}
              </button>
            </div>
            <div id="mm-status" class="status-indicator">
              <span class="status-dot status-success"></span>
              <span class="status-text">${t('metrics_manager_status_idle')}</span>
            </div>
          </section>

          <!-- System Metrics -->
          <section class="system-section">
            <h3><span class="icon">💻</span> ${t('metrics_manager_system_title')}</h3>
            <div id="mm-system-grid" class="system-grid">
              <div class="metric-card">
                <span class="metric-icon">⏱️</span>
                <span id="mm-uptime" class="metric-value">-</span>
                <span class="metric-label">${t('metrics_manager_system_uptime')}</span>
              </div>
              <div class="metric-card">
                <span class="metric-icon">📈</span>
                <span id="mm-collected" class="metric-value">0</span>
                <span class="metric-label">${t('metrics_manager_system_collected')}</span>
              </div>
              <div class="metric-card">
                <span class="metric-icon">🎯</span>
                <span id="mm-unique" class="metric-value">0</span>
                <span class="metric-label">${t('metrics_manager_system_unique')}</span>
              </div>
              <div class="metric-card">
                <span class="metric-icon">🔢</span>
                <span id="mm-counters-count" class="metric-value">0</span>
                <span class="metric-label">${t('metrics_manager_system_counters')}</span>
              </div>
            </div>
          </section>

          <!-- Alerts Section -->
          <section class="alerts-section">
            <h3>
              <span class="icon">🚨</span> ${t('metrics_manager_alerts_title')}
              <button id="mm-clear-alerts" class="btn btn-sm btn-secondary" style="margin-left: auto;">
                ${t('metrics_manager_clear_alerts')}
              </button>
            </h3>
            <div id="mm-alerts-list" class="alerts-list">
              <p class="empty-state">${t('metrics_manager_alerts_empty')}</p>
            </div>
          </section>

          <!-- Counters Table -->
          <section class="counters-section">
            <h3><span class="icon">🔢</span> ${t('metrics_manager_counters_title')}</h3>
            <table class="metrics-table">
              <thead>
                <tr>
                  <th>Metric Name</th>
                  <th style="text-align: right;">Value</th>
                </tr>
              </thead>
              <tbody id="mm-counters-body">
                <tr class="empty-row"><td colspan="2">${t('metrics_manager_counters_empty')}</td></tr>
              </tbody>
            </table>
          </section>

          <!-- Gauges Table -->
          <section class="gauges-section">
            <h3><span class="icon">📊</span> ${t('metrics_manager_gauges_title')}</h3>
            <table class="metrics-table">
              <thead>
                <tr>
                  <th>Metric Name</th>
                  <th>Type</th>
                  <th style="text-align: right;">Current</th>
                  <th style="text-align: right;">Avg</th>
                  <th style="text-align: right;">Min</th>
                  <th style="text-align: right;">Max</th>
                </tr>
              </thead>
              <tbody id="mm-gauges-body">
                <tr class="empty-row"><td colspan="6">${t('metrics_manager_gauges_empty')}</td></tr>
              </tbody>
            </table>
          </section>

          <!-- Metric History Chart -->
          <section class="history-section">
            <h3><span class="icon">📉</span> ${t('metrics_manager_history_title')}</h3>
            <div class="history-select">
              <select id="mm-metric-select">
                <option value="">${t('metrics_manager_history_select')}</option>
              </select>
              <select id="mm-time-range">
                <option value="50">50 points</option>
                <option value="100" selected>100 points</option>
                <option value="200">200 points</option>
                <option value="500">500 points</option>
              </select>
            </div>
            <div class="chart-container">
              <div class="chart-area">
                <canvas id="mm-history-chart" class="chart-canvas"></canvas>
                <div id="mm-chart-placeholder" class="chart-placeholder">${t('metrics_manager_history_select')}</div>
              </div>
            </div>
          </section>

          <!-- Plugin Metrics -->
          <section class="plugins-section">
            <h3><span class="icon">🔌</span> ${t('metrics_manager_plugins_title')}</h3>
            <div id="mm-plugins-list" class="plugin-metrics-list">
              <p class="empty-state">${t('metrics_manager_plugins_empty')}</p>
            </div>
          </section>

          <!-- Logs Section -->
          <section class="logs-section">
            <div class="logs-header">
              <h3><span class="icon">📜</span> ${t('metrics_manager_logs_title')}</h3>
              <div class="logs-controls">
                <select id="mm-log-level">
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO" selected>INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
                <input type="text" id="mm-log-search" placeholder="${t('metrics_manager_logs_search')}" />
                <button id="mm-logs-pause" class="btn btn-sm btn-secondary">
                  ${t('metrics_manager_logs_pause')}
                </button>
                <button id="mm-logs-download" class="btn btn-sm btn-secondary">
                  ${t('metrics_manager_logs_download')}
                </button>
              </div>
            </div>
            <pre id="mm-logs-output" class="logs-stream"></pre>
          </section>
        </div>

        <!-- Sidebar -->
        <aside class="plugin-sidebar">
          <!-- Plugin Stats -->
          <section class="stats-section">
            <h3><span class="icon">📈</span> ${t('metrics_manager_stats_title')}</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">${t('metrics_manager_stats_collections')}</span>
                <span id="mm-stat-collections" class="stat-value">0</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('metrics_manager_stats_api_calls')}</span>
                <span id="mm-stat-api" class="stat-value">0</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('metrics_manager_stats_exports')}</span>
                <span id="mm-stat-exports" class="stat-value">0</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('metrics_manager_stats_errors')}</span>
                <span id="mm-stat-errors" class="stat-value">0</span>
              </div>
            </div>
          </section>

          <!-- Help Panel -->
          <div class="plugin-help">
            <h3>${t('metrics_manager_help_title')}</h3>
            <p>${t('metrics_manager_help_description')}</p>
            <h4 style="margin: 12px 0 8px; font-size: 13px;">${t('metrics_manager_help_features')}</h4>
            <ul>
              <li>${t('metrics_manager_help_feature_1')}</li>
              <li>${t('metrics_manager_help_feature_2')}</li>
              <li>${t('metrics_manager_help_feature_3')}</li>
              <li>${t('metrics_manager_help_feature_4')}</li>
              <li>${t('metrics_manager_help_feature_5')}</li>
            </ul>
            <a href="/docs/plugins/metrics_manager" target="_blank">${t('metrics_manager_help_link')}</a>
          </div>
        </aside>
      </div>
    </div>
  `;

  // === DOM References ===
  const refreshBtn = container.querySelector('#mm-refresh');
  const exportJsonBtn = container.querySelector('#mm-export-json');
  const exportPrometheusBtn = container.querySelector('#mm-export-prometheus');
  const resetBtn = container.querySelector('#mm-reset');
  const clearAlertsBtn = container.querySelector('#mm-clear-alerts');
  const statusDot = container.querySelector('.status-dot');
  const statusText = container.querySelector('.status-text');
  const metricSelect = container.querySelector('#mm-metric-select');
  const timeRange = container.querySelector('#mm-time-range');
  const logsPauseBtn = container.querySelector('#mm-logs-pause');
  const logsDownloadBtn = container.querySelector('#mm-logs-download');
  const logsOutput = container.querySelector('#mm-logs-output');
  const logLevel = container.querySelector('#mm-log-level');
  const logSearch = container.querySelector('#mm-log-search');

  // === Helper Functions ===
  function formatUptime(seconds) {
    if (!seconds || seconds < 0) return '-';
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  }

  function formatNumber(num) {
    if (typeof num !== 'number') return num;
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toFixed(2).replace(/\.?0+$/, '');
  }

  function setStatus(type, text) {
    statusDot.className = 'status-dot';
    if (type === 'success') statusDot.classList.add('status-success');
    else if (type === 'running') statusDot.classList.add('status-running');
    else if (type === 'error') statusDot.classList.add('status-error');
    else if (type === 'warning') statusDot.classList.add('status-warning');
    statusText.textContent = text;
  }

  function resolveApiBaseUrl() {
    if (bridge.api?.baseUrl) return bridge.api.baseUrl;
    if (bridge.state?.apiBaseUrl) return bridge.state.apiBaseUrl;
    try {
      const { origin } = window.location;
      if (origin.includes(':8050')) return origin.replace(':8050', ':8000');
      if (origin.includes(':8081')) return origin.replace(':8081', ':8000');
      return origin;
    } catch (err) {
      console.warn('[MetricsManager] Failed to resolve API base URL, falling back to 127.0.0.1:8000', err);
      return 'http://127.0.0.1:8000';
    }
  }

  // === API Functions ===
  async function fetchAllMetrics() {
    setStatus('running', t('metrics_manager_status_collecting'));
    try {
      const data = await bridge.api.get('/metrics_manager/all');
      if (!data || typeof data !== 'object') {
        throw new Error('Invalid metrics payload');
      }
      allMetrics = data;
      updateUI(allMetrics);
      setStatus('success', t('metrics_manager_status_healthy'));
    } catch (err) {
      console.error('Failed to fetch metrics:', err);
      setStatus('error', t('metrics_manager_status_error'));
    }
  }

  async function fetchPluginStats() {
    try {
      const stats = await bridge.api.get('/metrics_manager/metrics');
      updatePluginStats(stats);
    } catch (err) {
      console.error('Failed to fetch plugin stats:', err);
    }
  }

  async function fetchAlerts() {
    try {
      const data = await bridge.api.get('/metrics_manager/alerts');
      updateAlerts(data.alerts || []);
    } catch (err) {
      console.error('Failed to fetch alerts:', err);
    }
  }

  async function exportMetrics(format) {
    try {
      const content = await bridge.api.get(`/metrics_manager/export?format=${format}`, { responseType: 'text' });
      
      const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `jupiter-metrics.${format === 'json' ? 'json' : 'txt'}`;
      a.click();
      URL.revokeObjectURL(url);
      
      bridge.notify?.({ type: 'success', message: t('metrics_manager_export_success') });
    } catch (err) {
      console.error('Failed to export metrics:', err);
      bridge.notify?.({ type: 'error', message: `Export failed: ${err.message}` });
    }
  }

  async function resetAllMetrics() {
    if (!confirm('Are you sure you want to reset all metrics?')) return;
    try {
      await bridge.api.post('/metrics_manager/reset');
      await fetchAllMetrics();
    } catch (err) {
      console.error('Failed to reset metrics:', err);
    }
  }

  async function clearAllAlerts() {
    try {
      await bridge.api.delete('/metrics_manager/alerts');
      await fetchAlerts();
    } catch (err) {
      console.error('Failed to clear alerts:', err);
    }
  }

  async function fetchMetricHistory(metricName) {
    if (!metricName) {
      container.querySelector('#mm-chart-placeholder').style.display = 'flex';
      return;
    }
    try {
      const limit = timeRange.value;
      const data = await bridge.api.get(`/metrics_manager/history/${encodeURIComponent(metricName)}?limit=${limit}`);
      renderChart(data.points || []);
    } catch (err) {
      console.error('Failed to fetch metric history:', err);
    }
  }

  // === UI Update Functions ===
  function updateUI(data) {
    if (!data || typeof data !== 'object') {
      console.warn('Metrics payload is empty or invalid, skipping update');
      setStatus('warning', t('metrics_manager_status_error'));
      return;
    }
    // Update system metrics
    const system = data.system || {};
    container.querySelector('#mm-uptime').textContent = formatUptime(system.uptime_seconds);
    container.querySelector('#mm-collected').textContent = formatNumber(system.metrics_collected || 0);
    container.querySelector('#mm-unique').textContent = system.unique_metrics || 0;
    container.querySelector('#mm-counters-count').textContent = system.counters_tracked || 0;

    // Update counters table
    const countersBody = container.querySelector('#mm-counters-body');
    const counters = data.counters || {};
    const counterKeys = Object.keys(counters);
    
    if (counterKeys.length === 0) {
      countersBody.innerHTML = `<tr class="empty-row"><td colspan="2">${t('metrics_manager_counters_empty')}</td></tr>`;
    } else {
      countersBody.innerHTML = counterKeys.map(key => `
        <tr>
          <td class="metric-name">${key}</td>
          <td class="metric-value">${formatNumber(counters[key])}</td>
        </tr>
      `).join('');
    }

    // Update gauges table
    const gaugesBody = container.querySelector('#mm-gauges-body');
    const metrics = data.metrics || {};
    const metricKeys = Object.keys(metrics);
    
    if (metricKeys.length === 0) {
      gaugesBody.innerHTML = `<tr class="empty-row"><td colspan="6">${t('metrics_manager_gauges_empty')}</td></tr>`;
    } else {
      const safeRows = metricKeys
        .map(key => [key, metrics[key]])
        .filter(([, m]) => m && typeof m === 'object')
        .map(([key, m]) => `
          <tr>
            <td class="metric-name">${m.name || key}</td>
            <td class="metric-type">${m.type || 'gauge'}</td>
            <td class="metric-value">${formatNumber(m.current)}</td>
            <td class="metric-value">${formatNumber(m.avg)}</td>
            <td class="metric-value">${formatNumber(m.min)}</td>
            <td class="metric-value">${formatNumber(m.max)}</td>
          </tr>
        `);
      gaugesBody.innerHTML = safeRows.length
        ? safeRows.join('')
        : `<tr class="empty-row"><td colspan="6">${t('metrics_manager_gauges_empty')}</td></tr>`;
    }

    // Update metric select options
    const currentSelection = metricSelect.value;
    metricSelect.innerHTML = `<option value="">${t('metrics_manager_history_select')}</option>`;
    metricKeys.forEach(key => {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = key;
      metricSelect.appendChild(option);
    });
    if (currentSelection && metricKeys.includes(currentSelection)) {
      metricSelect.value = currentSelection;
    }

    // Update plugin metrics
    const pluginsList = container.querySelector('#mm-plugins-list');
    const plugins = data.plugins || {};
    const pluginKeys = Object.keys(plugins);
    
    if (pluginKeys.length === 0) {
      pluginsList.innerHTML = `<p class="empty-state">${t('metrics_manager_plugins_empty')}</p>`;
    } else {
      const pluginCards = pluginKeys
        .map(pluginId => {
          const pMetrics = plugins[pluginId];
          if (!pMetrics || typeof pMetrics !== 'object') {
            return '';
          }
          const metricsHtml = Object.entries(pMetrics).map(([k, v]) => {
            if (v && typeof v === 'object') {
              return Object.entries(v)
                .filter(([, subV]) => subV !== null && subV !== undefined)
                .map(([subK, subV]) => 
                  `<tr><td class="metric-name">${k}.${subK}</td><td class="metric-value">${formatNumber(subV)}</td></tr>`
                ).join('');
            }
            if (v === null || v === undefined) return '';
            return `<tr><td class="metric-name">${k}</td><td class="metric-value">${formatNumber(v)}</td></tr>`;
          }).join('');
          
          if (!metricsHtml) {
            return '';
          }
          
          return `
            <div class="plugin-metrics-item">
              <div class="plugin-metrics-header">
                <span class="plugin-metrics-name">
                  <span class="chevron">▶</span>
                  🔌 ${pluginId}
                </span>
              </div>
              <div class="plugin-metrics-body">
                <table class="metrics-table">
                  <tbody>${metricsHtml}</tbody>
                </table>
              </div>
            </div>
          `;
        })
        .filter(Boolean);

      pluginsList.innerHTML = pluginCards.length
        ? pluginCards.join('')
        : `<p class="empty-state">${t('metrics_manager_plugins_empty')}</p>`;

      // Add click handlers for accordion
      pluginsList.querySelectorAll('.plugin-metrics-header').forEach(header => {
        header.addEventListener('click', () => {
          header.parentElement.classList.toggle('expanded');
        });
      });
    }
  }

  function updatePluginStats(stats) {
    const counters = stats.counters || {};
    container.querySelector('#mm-stat-collections').textContent = counters.collections || 0;
    container.querySelector('#mm-stat-api').textContent = counters.api_calls || 0;
    container.querySelector('#mm-stat-exports').textContent = counters.exports || 0;
    container.querySelector('#mm-stat-errors').textContent = counters.errors || 0;
  }

  function updateAlerts(alerts) {
    const alertsList = container.querySelector('#mm-alerts-list');
    
    if (alerts.length === 0) {
      alertsList.innerHTML = `<p class="empty-state">${t('metrics_manager_alerts_empty')}</p>`;
      return;
    }

    alertsList.innerHTML = alerts.map(alert => `
      <div class="alert-item severity-${alert.severity}">
        <span class="alert-icon">${alert.severity === 'critical' ? '🔴' : alert.severity === 'warning' ? '🟡' : 'ℹ️'}</span>
        <div class="alert-content">
          <div class="alert-message">${alert.message}</div>
          <div class="alert-details">${alert.metric_name} | Threshold: ${alert.threshold} | Value: ${formatNumber(alert.current_value)}</div>
        </div>
      </div>
    `).join('');
  }

  function renderChart(points) {
    const placeholder = container.querySelector('#mm-chart-placeholder');
    const canvas = container.querySelector('#mm-history-chart');
    
    if (points.length === 0) {
      placeholder.style.display = 'flex';
      return;
    }
    
    placeholder.style.display = 'none';
    
    // Simple canvas chart rendering (no external library)
    const ctx = canvas.getContext('2d');
    const rect = canvas.parentElement.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height - 40;
    
    const padding = { top: 20, right: 20, bottom: 30, left: 50 };
    const chartWidth = canvas.width - padding.left - padding.right;
    const chartHeight = canvas.height - padding.top - padding.bottom;
    
    const values = points.map(p => p.value);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 1;
    
    // Clear canvas
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--panel-contrast') || '#1a1a2e';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (chartHeight * i / 5);
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(canvas.width - padding.right, y);
      ctx.stroke();
    }
    
    // Draw Y-axis labels
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
      const val = maxVal - (range * i / 5);
      const y = padding.top + (chartHeight * i / 5);
      ctx.fillText(formatNumber(val), padding.left - 5, y + 3);
    }
    
    // Draw line
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#4a6cf7';
    ctx.lineWidth = 2;
    ctx.beginPath();
    
    points.forEach((p, i) => {
      const x = padding.left + (chartWidth * i / (points.length - 1 || 1));
      const y = padding.top + chartHeight - ((p.value - minVal) / range * chartHeight);
      
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    
    // Draw points
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--primary') || '#4a6cf7';
    points.forEach((p, i) => {
      const x = padding.left + (chartWidth * i / (points.length - 1 || 1));
      const y = padding.top + chartHeight - ((p.value - minVal) / range * chartHeight);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  // === Log Streaming ===
  function startLogStream() {
    if (logsEventSource) {
      logsEventSource.close();
    }
    
    // Use bridge.ws for streaming if available, fallback to direct SSE
    const baseUrl = resolveApiBaseUrl();
    logsEventSource = new EventSource(`${baseUrl}/metrics_manager/logs/stream`);
    
    logsEventSource.onmessage = (event) => {
      if (logsPaused) return;
      
      const line = event.data;
      const level = logLevel.value;
      const search = logSearch.value.toLowerCase();
      
      // Filter by level
      const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];
      const levelIndex = levels.indexOf(level);
      const lineLevel = levels.find(l => line.includes(l)) || 'DEBUG';
      if (levels.indexOf(lineLevel) < levelIndex) return;
      
      // Filter by search
      if (search && !line.toLowerCase().includes(search)) return;
      
      logsOutput.textContent += line + '\n';
      logsOutput.scrollTop = logsOutput.scrollHeight;
      
      // Keep only last 500 lines
      const lines = logsOutput.textContent.split('\n');
      if (lines.length > 500) {
        logsOutput.textContent = lines.slice(-500).join('\n');
      }
    };
    
    logsEventSource.onerror = () => {
      console.warn('Log stream disconnected, will retry...');
      setTimeout(() => startLogStream(), 3000);
    };
  }

  async function downloadLogs() {
    try {
      const content = await bridge.api.get('/metrics_manager/logs', { responseType: 'text' });
      
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'metrics_manager.log';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download logs:', err);
    }
  }

  // === Event Listeners ===
  refreshBtn.addEventListener('click', () => {
    fetchAllMetrics();
    fetchPluginStats();
    fetchAlerts();
  });

  exportJsonBtn.addEventListener('click', () => exportMetrics('json'));
  exportPrometheusBtn.addEventListener('click', () => exportMetrics('prometheus'));
  resetBtn.addEventListener('click', resetAllMetrics);
  clearAlertsBtn.addEventListener('click', clearAllAlerts);

  metricSelect.addEventListener('change', () => fetchMetricHistory(metricSelect.value));
  timeRange.addEventListener('change', () => fetchMetricHistory(metricSelect.value));

  logsPauseBtn.addEventListener('click', () => {
    logsPaused = !logsPaused;
    logsPauseBtn.textContent = logsPaused ? t('metrics_manager_logs_resume') : t('metrics_manager_logs_pause');
  });

  logsDownloadBtn.addEventListener('click', downloadLogs);

  // === Initialize ===
  fetchAllMetrics();
  fetchPluginStats();
  fetchAlerts();
  startLogStream();

  // Auto-refresh every 10 seconds
  refreshInterval = setInterval(() => {
    fetchAllMetrics();
    fetchPluginStats();
  }, 10000);

  // Return cleanup function
  return () => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
    if (logsEventSource) {
      logsEventSource.close();
      logsEventSource = null;
    }
  };
}

export function unmount() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
  if (logsEventSource) {
    logsEventSource.close();
    logsEventSource = null;
  }
}
