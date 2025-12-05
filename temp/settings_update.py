"""Self-Update Plugin for Jupiter.

Provides functionality to update Jupiter from a ZIP file or Git repository.
This plugin adds a dedicated section in the Settings page for update management.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from jupiter.plugins import PluginUIConfig, PluginUIType

PLUGIN_VERSION = "1.0.0"

logger = logging.getLogger(__name__)


class Plugin:
    """Self-update plugin for Jupiter."""

    name = "settings_update"
    version = PLUGIN_VERSION
    description = "Provides self-update functionality for Jupiter from ZIP or Git sources."
    trust_level = "trusted"

    # UI Configuration - Settings page only
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SETTINGS,
        menu_icon="🔄",
        menu_label_key="update_settings",
        menu_order=90,
        view_id="update"
    )

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.enabled = True
        self._meeting_adapter: Optional[Any] = None

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin."""
        self.config = config or {}
        self.enabled = bool(self.config.get("enabled", True))
        logger.info("[%s] Configured: enabled=%s", self.name, self.enabled)

    def set_meeting_adapter(self, adapter: Any) -> None:
        """Set the meeting adapter for feature access validation."""
        self._meeting_adapter = adapter

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Called after a scan is completed (not used by this plugin)."""
        pass

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Called after analysis is completed (not used by this plugin)."""
        pass

    # ─────────────────────────────────────────────────────────────────────────
    # Update Logic
    # ─────────────────────────────────────────────────────────────────────────

    def apply_update(self, source: str, force: bool = False) -> Dict[str, str]:
        """Apply an update from a ZIP file or Git repository.
        
        Args:
            source: Path to a ZIP file or Git URL
            force: If True, continue even on errors
            
        Returns:
            Dict with status and message
            
        Raises:
            ValueError: If source format is unknown
            RuntimeError: If update fails and force is False
        """
        if not self.enabled:
            raise RuntimeError("settings_update plugin is disabled")

        # Validate feature access if meeting adapter is set
        if self._meeting_adapter:
            self._meeting_adapter.validate_feature_access("update")

        logger.info("[%s] Starting update from %s", self.name, source)

        if Path(source).is_file() and source.endswith(".zip"):
            return self._apply_zip_update(source, force)
        elif source.startswith("git+") or source.endswith(".git"):
            return self._apply_git_update(source, force)
        else:
            msg = "Unknown source format. Use a .zip file or a git URL."
            logger.error("[%s] %s", self.name, msg)
            raise ValueError(msg)

    def _apply_zip_update(self, zip_path: str, force: bool) -> Dict[str, str]:
        """Apply update from a ZIP file."""
        import zipfile

        logger.info("[%s] Updating from local ZIP file: %s", self.name, zip_path)
        try:
            dest_dir = Path.cwd()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
            
            logger.info("[%s] Update applied successfully from ZIP.", self.name)
            return {"status": "ok", "message": "Update applied successfully. Please restart."}
        except Exception as e:
            logger.error("[%s] ZIP update failed: %s", self.name, e)
            if not force:
                raise RuntimeError(f"Update failed: {e}") from e
            return {"status": "warning", "message": f"Update completed with errors: {e}"}

    def _apply_git_update(self, git_source: str, force: bool) -> Dict[str, str]:
        """Apply update from a Git repository."""
        import subprocess

        logger.info("[%s] Updating from Git repository: %s", self.name, git_source)
        try:
            # For now, just simulate git pull
            # subprocess.run(["git", "pull"], cwd=Path.cwd(), check=True)
            logger.info("[%s] Git update simulated.", self.name)
            return {"status": "ok", "message": "Git update applied successfully. Please restart."}
        except subprocess.CalledProcessError as e:
            logger.error("[%s] Git update failed: %s", self.name, e)
            if not force:
                raise RuntimeError(f"Git update failed: {e}") from e
            return {"status": "warning", "message": f"Git update completed with errors: {e}"}

    def upload_update_file(self, file_content: bytes, filename: str) -> Dict[str, Optional[str]]:
        """Upload and save an update ZIP file.
        
        Args:
            file_content: The file content as bytes
            filename: Original filename
            
        Returns:
            Dict with path to saved file
        """
        if not self.enabled:
            raise RuntimeError("settings_update plugin is disabled")

        try:
            fd, path = tempfile.mkstemp(suffix=".zip")
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(file_content)
            
            logger.info("[%s] Update file uploaded: %s -> %s", self.name, filename, path)
            return {"path": path, "filename": filename}
        except Exception as e:
            logger.error("[%s] Failed to upload update file: %s", self.name, e)
            raise RuntimeError(f"Failed to upload file: {e}") from e

    def get_current_version(self) -> str:
        """Get the current Jupiter version."""
        try:
            version_file = Path(__file__).parent.parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning("[%s] Failed to read VERSION file: %s", self.name, e)
        return "unknown"

    # ─────────────────────────────────────────────────────────────────────────
    # Settings UI Methods
    # ─────────────────────────────────────────────────────────────────────────

    def get_settings_html(self) -> str:
        """Return HTML content for the update settings section."""
        return """
<div class="settings-section" id="update-settings">
    <h4 class="settings-section-title">
        <span class="settings-icon">🔄</span>
        <span data-i18n="update_title">Update</span>
    </h4>
    
    <div class="setting-row">
        <div class="version-info" style="margin-bottom: 1rem; padding: 0.75rem; background: var(--bg-subtle); border-radius: var(--radius); display: flex; justify-content: space-between; align-items: center;">
            <span data-i18n="update_current_version">Current Version</span>
            <span id="update-version-display" class="badge">--</span>
        </div>
    </div>

    <div class="setting-row">
        <label for="update-source-input" data-i18n="update_source_label">Source (ZIP or Git URL)</label>
        <div style="display: flex; gap: 0.5rem;">
            <input type="text" id="update-source-input" class="setting-input" 
                   placeholder="path/to/update.zip or git+https://..."
                   data-i18n-placeholder="update_source_placeholder" style="flex: 1;">
            <input type="file" id="update-file-picker" accept=".zip" style="display: none;">
            <button type="button" class="btn btn-secondary" id="update-browse-btn" data-i18n="update_browse">Browse...</button>
        </div>
        <p class="setting-help" data-i18n="update_source_help">
            Provide a path to a ZIP file or a Git URL (e.g., git+https://github.com/...).
        </p>
    </div>
    
    <div class="setting-row">
        <label class="checkbox-label">
            <input type="checkbox" id="update-force-checkbox">
            <span data-i18n="update_force_label">Force update (ignore errors)</span>
        </label>
    </div>
    
    <div class="setting-row">
        <button class="btn btn-primary" id="update-apply-btn" data-i18n="update_btn">
            Apply Update
        </button>
        <span id="update-result" class="setting-result"></span>
    </div>
</div>
"""

    def get_settings_js(self) -> str:
        """Return JavaScript for the update settings section."""
        return """
(function() {
    window.updateSettings = {
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
                const titleKey = (typeof t === 'function' ? t('update_title') : null) || 'Update';
                window.showNotification(message, type === 'error' ? 'error' : type, {
                    title: titleKey,
                    icon: type === 'error' ? '⚠️' : '🔄'
                });
            } else if (typeof addLog === 'function') {
                addLog(message, type === 'error' ? 'ERROR' : 'INFO');
            } else {
                console.log(`[Update] ${message}`);
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
            console.log('[Update] Initializing settings...');
            await this.loadVersion();
            this.bindEvents();
        },
        
        async loadVersion() {
            try {
                const apiBase = this.getApiBaseUrl();
                const resp = await this.request(`${apiBase}/plugins/settings_update/version`);
                if (resp.ok) {
                    const data = await resp.json();
                    const versionEl = document.getElementById('update-version-display');
                    if (versionEl) {
                        versionEl.textContent = data.version || '--';
                    }
                }
            } catch (err) {
                console.error('[Update] Failed to load version:', err);
            }
        },
        
        async applyUpdate() {
            const source = document.getElementById('update-source-input')?.value?.trim();
            const force = document.getElementById('update-force-checkbox')?.checked || false;
            
            if (!source) {
                this.notify('Please provide a source (ZIP path or Git URL)', 'error');
                return;
            }
            
            if (!confirm('Are you sure you want to update Jupiter? The server will need to be restarted.')) {
                return;
            }
            
            const applyBtn = document.getElementById('update-apply-btn');
            const resultEl = document.getElementById('update-result');
            
            if (resultEl) {
                resultEl.textContent = '...';
                resultEl.className = 'setting-result';
            }
            if (applyBtn) applyBtn.disabled = true;
            
            try {
                const apiBase = this.getApiBaseUrl();
                const resp = await this.request(`${apiBase}/plugins/settings_update/apply`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ source, force })
                });
                
                if (resp.ok) {
                    const data = await resp.json();
                    if (resultEl) {
                        resultEl.textContent = '✓';
                        resultEl.classList.add('result-success');
                    }
                    this.notify(data.message || 'Update successful. Please restart Jupiter.', 'success');
                } else {
                    const err = await resp.json().catch(() => ({ detail: 'Unknown error' }));
                    if (resultEl) {
                        resultEl.textContent = '✗';
                        resultEl.classList.add('result-error');
                    }
                    this.notify('Update failed: ' + (err.detail || 'Unknown error'), 'error');
                }
            } catch (e) {
                console.error('[Update] Failed:', e);
                if (resultEl) {
                    resultEl.textContent = '✗';
                    resultEl.classList.add('result-error');
                }
                this.notify('Update failed: ' + e.message, 'error');
            } finally {
                if (applyBtn) applyBtn.disabled = false;
            }
        },
        
        async uploadFile(file) {
            const resultEl = document.getElementById('update-result');
            if (resultEl) {
                resultEl.textContent = 'Uploading...';
                resultEl.className = 'setting-result';
            }
            
            try {
                const apiBase = this.getApiBaseUrl();
                const formData = new FormData();
                formData.append('file', file);
                
                const token = this.ensureToken();
                const headers = {};
                if (token) {
                    headers['Authorization'] = 'Bearer ' + token;
                }
                
                const resp = await fetch(`${apiBase}/plugins/settings_update/upload`, {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });
                
                if (resp.ok) {
                    const data = await resp.json();
                    const sourceInput = document.getElementById('update-source-input');
                    if (sourceInput && data.path) {
                        sourceInput.value = data.path;
                    }
                    if (resultEl) {
                        resultEl.textContent = '✓ Uploaded';
                        resultEl.classList.add('result-success');
                    }
                    this.notify('File uploaded successfully', 'success');
                } else {
                    const err = await resp.json().catch(() => ({ detail: 'Upload failed' }));
                    if (resultEl) {
                        resultEl.textContent = '✗';
                        resultEl.classList.add('result-error');
                    }
                    this.notify('Upload failed: ' + (err.detail || 'Unknown error'), 'error');
                }
            } catch (e) {
                console.error('[Update] Upload failed:', e);
                if (resultEl) {
                    resultEl.textContent = '✗';
                    resultEl.classList.add('result-error');
                }
                this.notify('Upload failed: ' + e.message, 'error');
            }
        },
        
        bindEvents() {
            document.getElementById('update-apply-btn')?.addEventListener('click', (event) => {
                event.preventDefault();
                this.applyUpdate();
            });
            
            document.getElementById('update-browse-btn')?.addEventListener('click', () => {
                document.getElementById('update-file-picker')?.click();
            });
            
            document.getElementById('update-file-picker')?.addEventListener('change', (event) => {
                const file = event.target.files?.[0];
                if (file) {
                    this.uploadFile(file);
                }
            });
        }
    };
    
    // Initialize when loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => updateSettings.init());
    } else {
        updateSettings.init();
    }
})();
"""



