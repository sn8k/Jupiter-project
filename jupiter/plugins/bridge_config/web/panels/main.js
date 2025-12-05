/**
 * web/panels/main.js – Bridge Config settings panel for WebUI.
 * Version: 1.0.0
 *
 * This file is dynamically loaded by the plugin receptacle.
 * Exports mount(container, bridge) called by the WebUI.
 * 
 * Conforme à plugins_architecture.md v0.4.0
 */

export function mount(container, bridge) {
  const t = bridge.i18n.t;
  
  // Panel structure
  container.innerHTML = `
    <div class="plugin-panel bridge-config-plugin">
      <header class="plugin-header">
        <h2>🔧 ${t('plugin.bridge_config.title')}</h2>
        <span class="plugin-version">v1.0.0</span>
      </header>
      
      <div class="plugin-body">
        <!-- Status Section -->
        <section class="status-section panel">
          <h3>${t('bridge_config_status_title')}</h3>
          <div id="bridge-status" class="status-grid">
            <div class="status-item">
              <span class="status-label">${t('bridge_config_status_bridge')}</span>
              <span id="bridge-available" class="status-value">-</span>
            </div>
            <div class="status-item">
              <span class="status-label">${t('bridge_config_status_dev_mode')}</span>
              <span id="dev-mode-status" class="status-value">-</span>
            </div>
            <div class="status-item">
              <span class="status-label">${t('bridge_config_status_governance')}</span>
              <span id="governance-mode" class="status-value">-</span>
            </div>
          </div>
        </section>

        <!-- Plugins Summary -->
        <section class="plugins-summary-section panel">
          <h3>${t('bridge_config_plugins_title')}</h3>
          <div id="plugins-summary" class="stats-grid">
            <div class="stat-item">
              <span class="stat-value" id="plugins-total">0</span>
              <span class="stat-label">${t('bridge_config_plugins_total')}</span>
            </div>
            <div class="stat-item stat-success">
              <span class="stat-value" id="plugins-ready">0</span>
              <span class="stat-label">${t('bridge_config_plugins_ready')}</span>
            </div>
            <div class="stat-item stat-error">
              <span class="stat-value" id="plugins-error">0</span>
              <span class="stat-label">${t('bridge_config_plugins_error')}</span>
            </div>
            <div class="stat-item stat-warning">
              <span class="stat-value" id="plugins-legacy">0</span>
              <span class="stat-label">${t('bridge_config_plugins_legacy')}</span>
            </div>
          </div>
        </section>

        <!-- Quick Actions -->
        <section class="actions-section panel">
          <h3>${t('bridge_config_actions_title')}</h3>
          <div class="action-buttons">
            <button id="btn-toggle-dev-mode" class="btn btn-secondary">
              <span class="btn-icon">🔧</span>
              ${t('bridge_config_toggle_dev_mode')}
            </button>
            <button id="btn-refresh-status" class="btn btn-secondary">
              <span class="btn-icon">🔄</span>
              ${t('bridge_config_refresh')}
            </button>
            <button id="btn-view-plugins" class="btn btn-secondary">
              <span class="btn-icon">📦</span>
              ${t('bridge_config_view_plugins')}
            </button>
          </div>
        </section>

        <!-- Dev Mode Details (shown when dev mode is active) -->
        <section id="dev-mode-section" class="dev-mode-section panel hidden">
          <h3>🛠️ ${t('bridge_config_dev_mode_title')}</h3>
          <div class="dev-mode-config">
            <div class="form-group">
              <label>
                <input type="checkbox" id="dev-allow-unsigned" />
                ${t('bridge_config_allow_unsigned')}
              </label>
            </div>
            <div class="form-group">
              <label>
                <input type="checkbox" id="dev-hot-reload" />
                ${t('bridge_config_hot_reload')}
              </label>
            </div>
            <div class="form-group">
              <label>
                <input type="checkbox" id="dev-verbose-logging" />
                ${t('bridge_config_verbose_logging')}
              </label>
            </div>
          </div>
        </section>

        <!-- Plugins List (expandable) -->
        <section id="plugins-list-section" class="plugins-list-section panel hidden">
          <h3>📦 ${t('bridge_config_plugins_list')}</h3>
          <div id="plugins-list" class="plugins-list"></div>
        </section>
      </div>
    </div>
  `;

  // State
  let devModeActive = false;
  let pluginsVisible = false;

  // Load initial status
  loadStatus();

  // Event handlers
  document.getElementById('btn-refresh-status').addEventListener('click', loadStatus);
  document.getElementById('btn-toggle-dev-mode').addEventListener('click', toggleDevMode);
  document.getElementById('btn-view-plugins').addEventListener('click', togglePluginsList);

  // Dev mode checkboxes
  ['dev-allow-unsigned', 'dev-hot-reload', 'dev-verbose-logging'].forEach(id => {
    const checkbox = document.getElementById(id);
    if (checkbox) {
      checkbox.addEventListener('change', saveDevModeConfig);
    }
  });

  async function loadStatus() {
    try {
      const response = await bridge.api.get('/bridge_config/status');
      if (response.ok) {
        const data = await response.json();
        updateStatusUI(data);
      }
    } catch (e) {
      console.error('[BridgeConfig] Failed to load status:', e);
    }

    // Load plugins summary
    try {
      const response = await bridge.api.get('/bridge_config/plugins-summary');
      if (response.ok) {
        const data = await response.json();
        updatePluginsSummary(data);
      }
    } catch (e) {
      console.error('[BridgeConfig] Failed to load plugins summary:', e);
    }
  }

  function updateStatusUI(data) {
    document.getElementById('bridge-available').textContent = 
      data.bridge_available ? '✅ ' + t('bridge_config_available') : '❌ ' + t('bridge_config_unavailable');
    document.getElementById('bridge-available').className = 
      'status-value ' + (data.bridge_available ? 'status-ok' : 'status-error');

    devModeActive = data.developer_mode_active || false;
    document.getElementById('dev-mode-status').textContent = 
      devModeActive ? '🔧 ' + t('bridge_config_active') : '⬚ ' + t('bridge_config_inactive');
    document.getElementById('dev-mode-status').className = 
      'status-value ' + (devModeActive ? 'status-warning' : '');

    const govMode = data.governance?.mode || 'disabled';
    document.getElementById('governance-mode').textContent = govMode;

    // Show/hide dev mode section
    const devSection = document.getElementById('dev-mode-section');
    if (devModeActive) {
      devSection.classList.remove('hidden');
      // Update checkboxes based on config
      if (data.config) {
        document.getElementById('dev-allow-unsigned').checked = data.config.allow_unsigned_plugins || false;
        document.getElementById('dev-hot-reload').checked = data.config.hot_reload_enabled || false;
        document.getElementById('dev-verbose-logging').checked = data.config.verbose_logging || false;
      }
    } else {
      devSection.classList.add('hidden');
    }
  }

  function updatePluginsSummary(data) {
    document.getElementById('plugins-total').textContent = data.total || 0;
    document.getElementById('plugins-ready').textContent = data.ready || 0;
    document.getElementById('plugins-error').textContent = data.error || 0;
    document.getElementById('plugins-legacy').textContent = 
      data.plugins?.filter(p => p.legacy).length || 0;

    // Store plugins for list view
    container._pluginsData = data.plugins || [];
  }

  async function toggleDevMode() {
    try {
      const endpoint = devModeActive ? '/bridge_config/dev-mode/disable' : '/bridge_config/dev-mode/enable';
      const response = await bridge.api.post(endpoint);
      if (response.ok) {
        loadStatus();
        bridge.toast.show(
          devModeActive ? t('bridge_config_dev_mode_disabled') : t('bridge_config_dev_mode_enabled'),
          'success'
        );
      }
    } catch (e) {
      console.error('[BridgeConfig] Failed to toggle dev mode:', e);
      bridge.toast.show(t('bridge_config_error'), 'error');
    }
  }

  async function saveDevModeConfig() {
    const config = {
      allow_unsigned_plugins: document.getElementById('dev-allow-unsigned').checked,
      hot_reload_enabled: document.getElementById('dev-hot-reload').checked,
      verbose_logging: document.getElementById('dev-verbose-logging').checked,
    };

    try {
      const response = await bridge.api.put('/bridge_config/config', { config });
      if (response.ok) {
        bridge.toast.show(t('bridge_config_saved'), 'success');
      }
    } catch (e) {
      console.error('[BridgeConfig] Failed to save config:', e);
    }
  }

  function togglePluginsList() {
    const section = document.getElementById('plugins-list-section');
    pluginsVisible = !pluginsVisible;
    
    if (pluginsVisible) {
      section.classList.remove('hidden');
      renderPluginsList();
    } else {
      section.classList.add('hidden');
    }
  }

  function renderPluginsList() {
    const listEl = document.getElementById('plugins-list');
    const plugins = container._pluginsData || [];
    
    if (plugins.length === 0) {
      listEl.innerHTML = `<p class="empty-state">${t('bridge_config_no_plugins')}</p>`;
      return;
    }

    listEl.innerHTML = plugins.map(p => `
      <div class="plugin-item ${p.state === 'error' ? 'plugin-error' : ''} ${p.legacy ? 'plugin-legacy' : ''}">
        <div class="plugin-info">
          <span class="plugin-name">${p.name || p.id}</span>
          <span class="plugin-version">v${p.version}</span>
          ${p.legacy ? '<span class="badge badge-warning">legacy</span>' : ''}
        </div>
        <div class="plugin-meta">
          <span class="plugin-type">${p.type}</span>
          <span class="plugin-state state-${p.state}">${p.state}</span>
        </div>
      </div>
    `).join('');
  }
}
