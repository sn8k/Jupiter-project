/**
 * web/panels/main.js – Panneau principal du plugin dans la WebUI.
 * Version: 0.2.0
 *
 * Ce fichier est chargé dynamiquement par le réceptacle de plugins.
 * Il exporte une fonction `mount(container, bridge)` appelée par la WebUI.
 */

export function mount(container, bridge) {
  // Récupérer les traductions du plugin
  const t = bridge.i18n.t; // fonction de traduction

  // Structure du panneau
  container.innerHTML = `
    <div class="plugin-panel example-plugin">
      <header class="plugin-header">
        <h2>${t('example_plugin_title')}</h2>
      </header>
      <div class="plugin-body">
        <div class="plugin-main">
          <!-- Zone de contrôle -->
          <section class="control-section">
            <button id="example-run-btn" class="btn btn-primary">
              ${t('example_run_action')}
            </button>
            <div id="example-status" class="status-indicator">
              <span class="status-dot"></span>
              <span class="status-text">${t('example_status_idle')}</span>
            </div>
          </section>

          <!-- Résultats / Output -->
          <section class="results-section">
            <h3>${t('example_results_title')}</h3>
            <pre id="example-output"></pre>
            <!-- Export -->
            <div class="export-actions">
              <button id="example-export-file" class="btn btn-secondary">
                ${t('example_export_file')}
              </button>
              <button id="example-export-ai" class="btn btn-secondary">
                ${t('example_export_ai')}
              </button>
            </div>
          </section>

          <!-- Panneau de logs temps réel (obligatoire selon §10.3) -->
          <section class="logs-section">
            <div class="logs-header">
              <h3>${t('example_logs_title')}</h3>
              <div class="logs-controls">
                <select id="example-log-level">
                  <option value="DEBUG">DEBUG</option>
                  <option value="INFO" selected>INFO</option>
                  <option value="WARNING">WARNING</option>
                  <option value="ERROR">ERROR</option>
                </select>
                <input type="text" id="example-log-search" placeholder="${t('example_logs_search')}" />
                <button id="example-logs-pause" class="btn btn-sm btn-secondary">
                  ${t('example_logs_pause')}
                </button>
                <button id="example-logs-download" class="btn btn-sm btn-secondary">
                  ${t('example_logs_download')}
                </button>
              </div>
            </div>
            <pre id="example-logs-output" class="logs-stream"></pre>
          </section>

          <!-- Statistiques d'utilisation (§10.4) -->
          <section class="stats-section">
            <h3>${t('example_stats_title')}</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">${t('example_stats_executions')}</span>
                <span id="example-stat-executions" class="stat-value">0</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('example_stats_last_run')}</span>
                <span id="example-stat-last-run" class="stat-value">-</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">${t('example_stats_avg_duration')}</span>
                <span id="example-stat-avg-duration" class="stat-value">-</span>
              </div>
            </div>
          </section>
        </div>

        <!-- Panneau d'aide à droite (obligatoire selon §9) -->
        <aside class="plugin-help">
          <h3>${t('example_help_title')}</h3>
          <p>${t('example_help_description')}</p>
          <a href="/docs/plugins/example" target="_blank">${t('example_help_link')}</a>
        </aside>
      </div>
    </div>
  `;

  // === Bindings principaux ===
  const runBtn = container.querySelector('#example-run-btn');
  const statusText = container.querySelector('.status-text');
  const output = container.querySelector('#example-output');
  const exportFileBtn = container.querySelector('#example-export-file');
  const exportAiBtn = container.querySelector('#example-export-ai');

  let lastResult = null;

  runBtn.addEventListener('click', async () => {
    statusText.textContent = t('example_status_running');
    try {
      const res = await bridge.api.post('/example', { action: 'run' });
      lastResult = res;
      output.textContent = JSON.stringify(res, null, 2);
      statusText.textContent = t('example_status_done');
      loadStats(); // Refresh stats after execution
    } catch (err) {
      output.textContent = `Error: ${err.message}`;
      statusText.textContent = t('example_status_error');
    }
  });

  exportFileBtn.addEventListener('click', () => {
    if (!lastResult) return;
    const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'example_export.json';
    a.click();
    URL.revokeObjectURL(url);
  });

  exportAiBtn.addEventListener('click', async () => {
    // Export vers agent IA via Bridge (modèle pylance analyzer)
    if (!lastResult) return;
    await bridge.ai.sendContext('example_plugin', lastResult);
    bridge.notify.info(t('example_export_ai_done'));
  });

  // === Logs temps réel ===
  const logsOutput = container.querySelector('#example-logs-output');
  const logLevelSelect = container.querySelector('#example-log-level');
  const logSearchInput = container.querySelector('#example-log-search');
  const pauseBtn = container.querySelector('#example-logs-pause');
  const downloadLogsBtn = container.querySelector('#example-logs-download');

  let logsPaused = false;
  let logsBuffer = [];
  let ws = null;

  function connectLogsStream() {
    ws = bridge.ws.connect('/example/logs/stream');
    ws.onmessage = (event) => {
      if (logsPaused) return;
      const logEntry = JSON.parse(event.data);
      const levelFilter = logLevelSelect.value;
      const searchFilter = logSearchInput.value.toLowerCase();

      // Filtrage par niveau
      const levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR'];
      if (levels.indexOf(logEntry.level) < levels.indexOf(levelFilter)) return;

      // Filtrage par recherche
      if (searchFilter && !logEntry.message.toLowerCase().includes(searchFilter)) return;

      logsBuffer.push(logEntry);
      if (logsBuffer.length > 500) logsBuffer.shift(); // Limite buffer

      const line = `[${logEntry.timestamp}] [${logEntry.level}] ${logEntry.message}`;
      logsOutput.textContent += line + '\n';
      logsOutput.scrollTop = logsOutput.scrollHeight; // Auto-scroll
    };
  }

  pauseBtn.addEventListener('click', () => {
    logsPaused = !logsPaused;
    pauseBtn.textContent = logsPaused ? t('example_logs_resume') : t('example_logs_pause');
  });

  downloadLogsBtn.addEventListener('click', async () => {
    // Télécharger le fichier log complet via API
    const response = await bridge.api.get('/example/logs', { responseType: 'blob' });
    const blob = new Blob([response], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'example_plugin.log';
    a.click();
    URL.revokeObjectURL(url);
  });

  // === Statistiques ===
  async function loadStats() {
    try {
      const metrics = await bridge.api.get('/example/metrics');
      container.querySelector('#example-stat-executions').textContent = metrics.example_plugin_executions_total || 0;
      container.querySelector('#example-stat-last-run').textContent = metrics.example_plugin_last_execution || '-';
      container.querySelector('#example-stat-avg-duration').textContent = 
        metrics.example_plugin_avg_duration_ms ? `${Math.round(metrics.example_plugin_avg_duration_ms)} ms` : '-';
    } catch (err) {
      console.error('Failed to load stats', err);
    }
  }

  // Init
  connectLogsStream();
  loadStats();
}

export function unmount(container) {
  // Cleanup WebSocket si nécessaire
  container.innerHTML = '';
}
