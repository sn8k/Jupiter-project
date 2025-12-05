"""
Notifications Webhook - UI Components

This module provides HTML and JavaScript for the settings UI.

@version 1.0.0
"""

from __future__ import annotations


def get_settings_html() -> str:
    """Return HTML content for the notifications settings section."""
    return _SETTINGS_HTML


def get_settings_js() -> str:
    """Return JavaScript for the notifications settings section."""
    return _SETTINGS_JS


# =============================================================================
# SETTINGS HTML
# =============================================================================

_SETTINGS_HTML = """
<div class="settings-section" id="notifications-settings">
    <h4 class="settings-section-title">
        <span class="settings-icon">🔔</span>
        <span data-i18n="notifications_title">Notifications</span>
    </h4>
    
    <div class="setting-row">
        <label for="notifications-enabled" data-i18n="notifications_enabled_label">Enable Notifications</label>
        <input type="checkbox" id="notifications-enabled" class="toggle-switch" checked>
    </div>
    
    <div class="setting-row">
        <label for="notifications-url" data-i18n="notifications_url_label">Webhook URL</label>
        <input type="url" id="notifications-url" class="setting-input" 
               placeholder="https://your-webhook.example.com/notify"
               data-i18n-placeholder="notifications_url_placeholder">
        <p class="setting-help" data-i18n="notifications_url_help">
            Leave empty to use local notifications only (displayed in the UI).
        </p>
    </div>
    
    <div class="setting-row">
        <label data-i18n="notifications_events_label">Events to Notify</label>
        <div class="checkbox-group">
            <label class="checkbox-label">
                <input type="checkbox" id="notify-scan-complete" checked>
                <span data-i18n="notifications_event_scan">Scan Complete</span>
            </label>
            <label class="checkbox-label">
                <input type="checkbox" id="notify-analysis-complete">
                <span data-i18n="notifications_event_analysis">Analysis Complete</span>
            </label>
            <label class="checkbox-label">
                <input type="checkbox" id="notify-quality-alert">
                <span data-i18n="notifications_event_quality">Quality Alerts</span>
            </label>
            <label class="checkbox-label">
                <input type="checkbox" id="notify-api-connected" checked>
                <span data-i18n="notifications_event_api">API Connected</span>
            </label>
        </div>
    </div>
    
    <div class="setting-row">
        <button class="btn btn-primary" id="notifications-save-btn" data-i18n="notifications_save">
            Save
        </button>
        <span id="notifications-save-result" class="setting-result"></span>
    </div>

    <div class="setting-row">
        <button class="btn btn-secondary" id="notifications-test-btn" data-i18n="notifications_test">
            Test Notification
        </button>
        <span id="notifications-test-result" class="setting-result"></span>
    </div>
</div>
"""


# =============================================================================
# SETTINGS JAVASCRIPT
# =============================================================================

_SETTINGS_JS = """
(function() {
    window.notificationsSettings = {
        getApiBaseUrl() {
            if (typeof state !== 'undefined' && state.apiBaseUrl) {
                return state.apiBaseUrl;
            }
            return window.location.protocol + '//' + window.location.hostname + ':8000';
        },

        ensureToken() {
            if (typeof state !== 'undefined' && state.token) {
                return state.token;
            }
            const stored = localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
            if (stored && typeof state !== 'undefined') {
                state.token = stored;
            }
            return stored;
        },

        notify(message, type = 'info') {
            if (typeof window.showNotification === 'function') {
                const titleKey = (typeof t === 'function' ? t('notifications_title') : null) || 'Notifications';
                window.showNotification(message, type === 'error' ? 'error' : type, {
                    title: titleKey,
                    icon: type === 'error' ? '⚠️' : '🔔'
                });
            } else if (typeof addLog === 'function') {
                addLog(message, type === 'error' ? 'ERROR' : 'INFO');
            } else {
                console.log(`[Notifications] ${message}`);
            }
        },

        async request(url, options = {}) {
            const opts = { ...options };
            opts.method = opts.method || 'GET';
            const headers = Object.assign({ 'Accept': 'application/json' }, opts.headers || {});
            const token = this.ensureToken();
            if (token && !headers['Authorization']) {
                headers['Authorization'] = 'Bearer ' + token;
            }
            opts.headers = headers;

            if (typeof apiFetch === 'function') {
                return apiFetch(url, opts);
            }
            return fetch(url, opts);
        },
        
        async init() {
            console.log('[Notifications] Initializing settings...');
            await this.loadSettings();
            this.bindEvents();
        },
        
        async loadSettings() {
            try {
                const apiBase = this.getApiBaseUrl();
                const resp = await this.request(`${apiBase}/plugins/notifications_webhook/config`);
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                
                const pluginConfig = await resp.json() || {};
                
                document.getElementById('notifications-enabled').checked = pluginConfig.enabled !== false;
                document.getElementById('notifications-url').value = pluginConfig.url || '';
                
                const events = Array.isArray(pluginConfig.events) && pluginConfig.events.length
                    ? pluginConfig.events
                    : ['scan_complete', 'api_connected'];
                document.getElementById('notify-scan-complete').checked = events.includes('scan_complete');
                document.getElementById('notify-analysis-complete').checked = events.includes('analysis_complete');
                document.getElementById('notify-quality-alert').checked = events.includes('quality_alert');
                document.getElementById('notify-api-connected').checked = events.includes('api_connected');
                
                const saveResult = document.getElementById('notifications-save-result');
                if (saveResult) saveResult.textContent = '';
            } catch (err) {
                console.error('[Notifications] Failed to load settings:', err);
                this.notify('Failed to load notifications settings', 'error');
            }
        },
        
        async saveSettings() {
            const events = [];
            if (document.getElementById('notify-scan-complete').checked) events.push('scan_complete');
            if (document.getElementById('notify-analysis-complete').checked) events.push('analysis_complete');
            if (document.getElementById('notify-quality-alert').checked) events.push('quality_alert');
            if (document.getElementById('notify-api-connected').checked) events.push('api_connected');
            
            const pluginConfig = {
                enabled: document.getElementById('notifications-enabled').checked,
                url: document.getElementById('notifications-url').value.trim() || null,
                events: events
            };
            
            const saveBtn = document.getElementById('notifications-save-btn');
            const resultEl = document.getElementById('notifications-save-result');
            if (resultEl) {
                resultEl.textContent = '...';
                resultEl.className = 'setting-result';
            }
            if (saveBtn) saveBtn.disabled = true;
            
            try {
                const apiBase = this.getApiBaseUrl();
                const resp = await this.request(`${apiBase}/plugins/notifications_webhook/config`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(pluginConfig)
                });
                
                if (resp.ok) {
                    if (resultEl) {
                        resultEl.textContent = '✓';
                        resultEl.classList.add('result-success');
                    }
                    this.notify('Notifications settings saved!', 'success');
                } else {
                    const errorText = await resp.text();
                    console.error('[Notifications] Failed to save settings:', errorText);
                    if (resultEl) {
                        resultEl.textContent = '✗';
                        resultEl.classList.add('result-error');
                    }
                    this.notify('Failed to save settings', 'error');
                }
            } catch (err) {
                console.error('[Notifications] Failed to save settings:', err);
                if (resultEl) {
                    resultEl.textContent = '✗';
                    resultEl.classList.add('result-error');
                }
                this.notify('Error saving settings', 'error');
            } finally {
                if (saveBtn) saveBtn.disabled = false;
            }
        },
        
        async testNotification() {
            const resultEl = document.getElementById('notifications-test-result');
            if (resultEl) {
                resultEl.textContent = '...';
                resultEl.className = 'setting-result';
            }
            
            try {
                const apiBase = this.getApiBaseUrl();
                const resp = await this.request(`${apiBase}/plugins/notifications_webhook/test`, {
                    method: 'POST'
                });
                
                if (resp.ok) {
                    this.notify('Test notification dispatched', 'success');
                    if (resultEl) {
                        resultEl.textContent = '✓ Sent!';
                        resultEl.classList.add('result-success');
                    }
                } else {
                    const errorText = await resp.text();
                    console.error('[Notifications] Test notification failed:', errorText);
                    if (resultEl) {
                        resultEl.textContent = '✗ Failed';
                        resultEl.classList.add('result-error');
                    }
                    this.notify('Failed to trigger test notification', 'error');
                }
            } catch (err) {
                if (resultEl) {
                    resultEl.textContent = '✗ Error';
                    resultEl.classList.add('result-error');
                }
                this.notify('Error triggering test notification', 'error');
            }
        },
        
        bindEvents() {
            document.getElementById('notifications-save-btn')?.addEventListener('click', (event) => {
                event.preventDefault();
                this.saveSettings().catch(err => console.error('[Notifications] Save failed:', err));
            });
            document.getElementById('notifications-test-btn')?.addEventListener('click', (event) => {
                event.preventDefault();
                this.testNotification();
            });
        }
    };
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => notificationsSettings.init());
    } else {
        notificationsSettings.init();
    }
})();
"""
