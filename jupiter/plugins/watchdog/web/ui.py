"""
Watchdog - UI Components

This module provides HTML and JavaScript for the settings UI.

@version 1.0.0
"""

from __future__ import annotations


def get_settings_html() -> str:
    """Return HTML for the settings section."""
    return _SETTINGS_HTML


def get_settings_js() -> str:
    """Return JavaScript for the settings section."""
    return _SETTINGS_JS


# =============================================================================
# SETTINGS HTML
# =============================================================================

_SETTINGS_HTML = """
<div class="watchdog-settings">
    <header class="settings-header">
        <div>
            <p class="eyebrow" data-i18n="watchdog_eyebrow">Development</p>
            <h3 data-i18n="watchdog_title">Plugin Watchdog</h3>
            <p class="muted small" data-i18n="watchdog_description">
                Automatically reload plugins when their source files are modified.
                Useful during plugin development to avoid restarting Jupiter.
            </p>
        </div>
    </header>
    
    <div class="settings-content">
        <!-- Status Panel -->
        <div class="watchdog-status panel-inset" id="watchdog-status-panel">
            <div class="status-grid">
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_monitoring">Monitoring</span>
                    <span class="status-value" id="watchdog-status-monitoring">--</span>
                </div>
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_files">Watched Files</span>
                    <span class="status-value" id="watchdog-status-files">--</span>
                </div>
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_reloads">Reloads</span>
                    <span class="status-value" id="watchdog-status-reloads">--</span>
                </div>
                <div class="status-item">
                    <span class="status-label" data-i18n="watchdog_status_last">Last Reload</span>
                    <span class="status-value" id="watchdog-status-last">--</span>
                </div>
            </div>
        </div>
        
        <!-- Settings Form -->
        <div class="settings-form">
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="watchdog-enabled">
                    <span data-i18n="watchdog_enabled">Enable Plugin Watchdog</span>
                </label>
                <p class="hint" data-i18n="watchdog_enabled_hint">
                    Start monitoring plugin files for changes.
                </p>
            </div>
            
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="watchdog-auto-reload" checked>
                    <span data-i18n="watchdog_auto_reload">Auto-reload on change</span>
                </label>
                <p class="hint" data-i18n="watchdog_auto_reload_hint">
                    Automatically reload plugins when changes are detected.
                </p>
            </div>
            
            <div class="form-group">
                <label for="watchdog-interval" data-i18n="watchdog_interval">Check Interval (seconds)</label>
                <input type="range" id="watchdog-interval" min="0.5" max="10" step="0.5" value="2">
                <span class="range-value" id="watchdog-interval-value">2.0s</span>
                <p class="hint" data-i18n="watchdog_interval_hint">
                    How often to check for file changes.
                </p>
            </div>
        </div>
        
        <!-- Actions -->
        <div class="settings-actions">
            <button class="btn btn-secondary" id="watchdog-force-check" data-i18n="watchdog_force_check">
                🔍 Force Check Now
            </button>
            <button class="btn btn-secondary" id="watchdog-refresh-status" data-i18n="watchdog_refresh_status">
                🔄 Refresh Status
            </button>
            <button class="btn btn-primary" id="watchdog-save-settings" data-i18n="watchdog_save">
                💾 Save Watchdog Settings
            </button>
        </div>
        
        <!-- Watched Files List -->
        <details class="watchdog-files-details">
            <summary data-i18n="watchdog_watched_files">Watched Files</summary>
            <ul class="watchdog-files-list" id="watchdog-files-list">
                <li class="muted" data-i18n="watchdog_no_files">No files being watched</li>
            </ul>
        </details>
    </div>
</div>

<style>
.watchdog-settings {
    padding: 1rem 0;
}

.watchdog-status {
    background: var(--panel-bg, #1e1e1e);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1.5rem;
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
}

.status-item {
    text-align: center;
}

.status-label {
    display: block;
    font-size: 0.75rem;
    color: var(--muted);
    margin-bottom: 0.25rem;
}

.status-value {
    display: block;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--accent, #4fc3f7);
}

.status-value.active {
    color: var(--success, #66bb6a);
}

.status-value.inactive {
    color: var(--muted);
}

.settings-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.settings-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
}

.watchdog-files-details {
    margin-top: 1rem;
}

.watchdog-files-details summary {
    cursor: pointer;
    font-weight: 500;
    padding: 0.5rem 0;
}

.watchdog-files-list {
    list-style: none;
    padding: 0;
    margin: 0.5rem 0;
    font-size: 0.85rem;
    font-family: monospace;
}

.watchdog-files-list li {
    padding: 0.25rem 0.5rem;
    border-bottom: 1px solid var(--border);
}

.watchdog-files-list li:last-child {
    border-bottom: none;
}

.range-value {
    display: inline-block;
    min-width: 3rem;
    text-align: center;
    font-weight: 500;
}
</style>
"""


# =============================================================================
# SETTINGS JAVASCRIPT
# =============================================================================

_SETTINGS_JS = """
(function() {
    function getApiBase() {
        if (typeof state !== 'undefined' && state.apiBaseUrl) {
            return state.apiBaseUrl;
        }
        return window.location.protocol + '//' + window.location.hostname + ':8000';
    }
    
    function getAuthHeaders() {
        const token = localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        return headers;
    }
    
    const enabledCheckbox = document.getElementById('watchdog-enabled');
    const autoReloadCheckbox = document.getElementById('watchdog-auto-reload');
    const intervalSlider = document.getElementById('watchdog-interval');
    const intervalValue = document.getElementById('watchdog-interval-value');
    const saveBtn = document.getElementById('watchdog-save-settings');
    const forceCheckBtn = document.getElementById('watchdog-force-check');
    const refreshStatusBtn = document.getElementById('watchdog-refresh-status');
    const filesList = document.getElementById('watchdog-files-list');
    
    const statusMonitoring = document.getElementById('watchdog-status-monitoring');
    const statusFiles = document.getElementById('watchdog-status-files');
    const statusReloads = document.getElementById('watchdog-status-reloads');
    const statusLast = document.getElementById('watchdog-status-last');
    
    function notify(message, type = 'info') {
        if (window.showNotification) {
            window.showNotification(message, type);
        } else {
            console.log(`[${type}] ${message}`);
        }
    }
    
    async function loadConfig() {
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/config`, {
                headers: getAuthHeaders()
            });
            if (resp.ok) {
                const config = await resp.json();
                enabledCheckbox.checked = config.enabled || false;
                autoReloadCheckbox.checked = config.auto_reload !== false;
                intervalSlider.value = config.check_interval || 2;
                intervalValue.textContent = `${intervalSlider.value}s`;
            }
        } catch (e) {
            console.error('Failed to load watchdog config:', e);
        }
    }
    
    async function loadStatus() {
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/status`, {
                headers: getAuthHeaders()
            });
            if (resp.ok) {
                const status = await resp.json();
                
                statusMonitoring.textContent = status.monitoring ? '✅ Active' : '⏸️ Stopped';
                statusMonitoring.className = 'status-value ' + (status.monitoring ? 'active' : 'inactive');
                
                statusFiles.textContent = status.watched_files || 0;
                statusReloads.textContent = status.reload_count || 0;
                statusLast.textContent = status.last_reload || '--';
                
                if (status.files && status.files.length > 0) {
                    filesList.innerHTML = status.files.map(f => 
                        `<li>📄 ${f.path} <span class="muted">(${f.plugin})</span></li>`
                    ).join('');
                } else {
                    filesList.innerHTML = '<li class="muted">No files being watched</li>';
                }
            }
        } catch (e) {
            console.error('Failed to load watchdog status:', e);
        }
    }
    
    async function saveConfig() {
        const config = {
            enabled: enabledCheckbox.checked,
            auto_reload: autoReloadCheckbox.checked,
            check_interval: parseFloat(intervalSlider.value),
        };
        
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/config`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(config),
            });
            
            if (resp.ok) {
                notify(window.t ? window.t('watchdog_saved') : 'Watchdog settings saved', 'success');
                setTimeout(loadStatus, 500);
            } else {
                notify(window.t ? window.t('watchdog_save_error') : 'Error saving settings', 'error');
            }
        } catch (e) {
            console.error('Failed to save watchdog config:', e);
            notify('Error: ' + e.message, 'error');
        }
    }
    
    async function forceCheck() {
        try {
            const resp = await fetch(`${getApiBase()}/plugins/watchdog/check`, {
                method: 'POST',
                headers: getAuthHeaders()
            });
            if (resp.ok) {
                const result = await resp.json();
                notify(`Checked ${result.checked} files, reloaded ${result.reloaded}`, 'info');
                loadStatus();
            }
        } catch (e) {
            console.error('Force check failed:', e);
            notify('Force check failed: ' + e.message, 'error');
        }
    }
    
    intervalSlider.addEventListener('input', () => {
        intervalValue.textContent = `${intervalSlider.value}s`;
    });
    
    saveBtn.addEventListener('click', saveConfig);
    forceCheckBtn.addEventListener('click', forceCheck);
    refreshStatusBtn.addEventListener('click', loadStatus);
    
    loadConfig();
    loadStatus();
    
    setInterval(() => {
        if (enabledCheckbox.checked) {
            loadStatus();
        }
    }, 5000);
})();
"""
