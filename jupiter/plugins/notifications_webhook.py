"""Generic Webhook Notification Plugin for Jupiter."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

import httpx

from jupiter.core.events import JupiterEvent, PLUGIN_NOTIFICATION
from jupiter.plugins import PluginUIConfig, PluginUIType

PLUGIN_VERSION = "0.2.2"

try:  # pragma: no cover - optional dependency in CLI-only workflows
    from jupiter.server.ws import manager as ws_manager
except Exception:  # pragma: no cover - fallback when server stack not loaded
    ws_manager = None

logger = logging.getLogger(__name__)


class Plugin:
    name = "notifications_webhook"
    version = PLUGIN_VERSION
    description = "Sends notifications to a webhook URL or falls back to local events."
    trust_level = "trusted"
    default_events = ("scan_complete", "api_connected")
    
    # UI Configuration - Settings page only
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SETTINGS,
        menu_icon="🔔",
        menu_label_key="notifications_settings",
        menu_order=50,
        view_id="notifications"
    )

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.url: str | None = None
        self.events: set[str] = set(self.default_events)
        self.enabled = True
        self._last_api_status: str | None = None

    def configure(self, config: Dict[str, Any]):
        self.config = config or {}
        self.url = self.config.get("url") or None
        raw_events = self.config.get("events")
        if raw_events and isinstance(raw_events, (list, set, tuple)):
            self.events = {str(evt) for evt in raw_events if evt}
        else:
            self.events = set(self.default_events)
        if not self.events:
            self.events = set(self.default_events)

        self.enabled = bool(self.config.get("enabled", True))

        if not self.url:
            logger.info("[%s] No webhook URL configured; notifications will stay local.", self.name)
        logger.info(
            "[%s] Configured: enabled=%s url_set=%s events=%s",
            self.name,
            self.enabled,
            bool(self.url),
            sorted(self.events),
        )
        logger.debug("[%s] Raw config=%s", self.name, self.config)

    def hook_on_scan(self, report: Dict[str, Any]):
        """Compatibility shim for legacy hook naming."""
        self.on_scan(report)

    def on_scan(self, report: Dict[str, Any]):
        """Called after a scan is completed."""
        logger.debug(
            "[%s] on_scan triggered (enabled=%s events=%s)",
            self.name,
            self.enabled,
            sorted(self.events),
        )
        if not self.enabled:
            logger.debug("[%s] Plugin disabled; skipping scan hooks", self.name)
            return
        if "scan_complete" in self.events:
            file_count = len(report.get("files", []))
            summary: Dict[str, Any] = {
                "root": report.get("root"),
                "file_count": file_count,
                "timestamp": report.get("last_scan_timestamp"),
                "message": f"Scan completed ({file_count} files).",
            }
            if not self.url:
                summary["message"] += " Webhook URL not configured; delivered locally."

            logger.info(
                "[%s] Queueing scan_complete notification (%d files)",
                self.name,
                file_count,
            )
            logger.debug("[%s] scan_complete payload=%s", self.name, summary)
            self._schedule_notification("scan_complete", summary)
        self._handle_api_status(report)

    def on_analyze(self, summary: Dict[str, Any]):
        """Called after analysis (reserved for future events)."""
        return

    def _handle_api_status(self, report: Dict[str, Any]) -> None:
        if "api_connected" not in self.events:
            return

        api_info = report.get("api") or {}
        api_config = api_info.get("config") or {}
        base_url = api_config.get("base_url")
        if not base_url:
            return

        endpoints = api_info.get("endpoints") or []
        status = "online" if endpoints else "offline"
        logger.debug(
            "[%s] API status evaluation: %s (endpoints=%d)",
            self.name,
            status,
            len(endpoints),
        )
        if status == self._last_api_status:
            return

        self._last_api_status = status
        is_online = status == "online"
        payload: Dict[str, Any] = {
            "root": report.get("root"),
            "status": status,
            "base_url": base_url,
            "endpoint_count": len(endpoints),
            "message": (
                f"Project API {base_url} is online."
                if is_online
                else f"Project API {base_url} is offline or unreachable."
            ),
            "level": "success" if is_online else "error",
        }
        logger.info("[%s] API status changed -> %s", self.name, status)
        logger.debug("[%s] api_connected payload=%s", self.name, payload)
        self._schedule_notification("api_connected", payload)

    def _schedule_notification(self, event_alias: str, payload: Dict[str, Any]) -> None:
        if not self.enabled:
            logger.debug("[%s] Plugin disabled; not scheduling %s", self.name, event_alias)
            return
        if event_alias not in self.events:
            logger.debug("[%s] Event %s not enabled; skipping", self.name, event_alias)
            return
        logger.debug("[%s] Scheduling event %s", self.name, event_alias)

        async def runner() -> None:
            await self._dispatch_notification(event_alias, payload)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(runner())
            return

        loop.create_task(runner())

    async def _dispatch_notification(self, event_alias: str, payload: Dict[str, Any]) -> None:
        logger.debug(
            "[%s] Dispatching event %s via %s",
            self.name,
            event_alias,
            "webhook" if self.url else "local",
        )
        if self.url:
            await self._send_webhook(event_alias, payload)
        else:
            await self._emit_local_notification(event_alias, payload)

    async def run_test(self) -> Dict[str, Any]:
        """Send a synthetic notification to validate transport configuration."""
        if not self.enabled:
            raise RuntimeError("notifications_webhook plugin is disabled")

        payload: Dict[str, Any] = {
            "root": self.config.get("root"),
            "timestamp": asyncio.get_running_loop().time(),
            "message": "Test notification triggered from Jupiter settings.",
        }

        logger.info("[%s] Running transport test (webhook=%s)", self.name, bool(self.url))
        await self._dispatch_notification("test_notification", payload)

        return {
            "event": "test_notification",
            "transport": "webhook" if self.url else "local",
            "payload": payload,
        }

    async def _send_webhook(self, event_alias: str, payload: Dict[str, Any]):
        logger.info("[%s] Sending webhook for event: %s", self.name, event_alias)
        logger.debug("[%s] Webhook payload=%s", self.name, payload)
        if not self.url:
            logger.warning("[%s] Webhook URL not configured, skipping", self.name)
            return
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.url,
                    json={
                        "event": event_alias,
                        "payload": payload,
                        "timestamp": asyncio.get_running_loop().time(),
                    },
                    timeout=5.0,
                )
        except Exception as exc:
            logger.error("[%s] Failed to send webhook: %s", self.name, exc)

    async def _emit_local_notification(self, event_alias: str, payload: Dict[str, Any]) -> None:
        message = payload.get("message") or event_alias
        logger.info("[%s] %s", self.name, message)
        logger.debug("[%s] Local notification payload=%s", self.name, payload)

        if not ws_manager:
            return

        event_payload = {
            "source": self.name,
            "event": event_alias,
            "message": message,
            "details": payload,
        }
        try:
            await ws_manager.broadcast(JupiterEvent(type=PLUGIN_NOTIFICATION, payload=event_payload))
        except Exception as exc:  # pragma: no cover - log-only branch
            logger.warning("[%s] Failed to broadcast local notification: %s", self.name, exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Settings UI Methods - Provide HTML/JS for the Settings page
    # ─────────────────────────────────────────────────────────────────────────

    def get_settings_html(self) -> str:
        """Return HTML content for the notifications settings section."""
        return """
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

    def get_settings_js(self) -> str:
        """Return JavaScript for the notifications settings section."""
        return """
(function() {
    window.notificationsSettings = {
        getApiBaseUrl() {
            // Use the global state from app.js if available, otherwise infer from window location
            if (typeof state !== 'undefined' && state.apiBaseUrl) {
                return state.apiBaseUrl;
            }
            // Fallback: assume API is on port 8000
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
                return;
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
            if (typeof fetch === 'function') {
                return fetch(url, opts);
            }
            throw new Error('No fetch implementation available');
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
                if (!resp.ok) {
                    throw new Error(`HTTP ${resp.status}`);
                }
                
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
                    headers: {
                        'Content-Type': 'application/json'
                    },
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
            resultEl.textContent = '...';
            resultEl.className = 'setting-result';
            
            try {
                const apiBase = this.getApiBaseUrl();
                const resp = await this.request(`${apiBase}/plugins/notifications_webhook/test`, {
                    method: 'POST',
                });
                
                if (resp.ok) {
                    this.notify('Test notification dispatched', 'success');
                    resultEl.textContent = '✓ Sent!';
                    resultEl.classList.add('result-success');
                } else {
                    const errorText = await resp.text();
                    console.error('[Notifications] Test notification failed:', errorText);
                    resultEl.textContent = '✗ Failed';
                    resultEl.classList.add('result-error');
                    this.notify('Failed to trigger test notification', 'error');
                }
            } catch (err) {
                resultEl.textContent = '✗ Error';
                resultEl.classList.add('result-error');
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
    
    // Initialize when loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => notificationsSettings.init());
    } else {
        notificationsSettings.init();
    }
})();
"""
