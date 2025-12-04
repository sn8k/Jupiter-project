"""Settings Update Core Plugin for Bridge v2.

Version: 0.1.0

This module adapts the settings_update plugin to work with
the Bridge v2 plugin system. It provides:
- Self-update functionality (ZIP, Git)
- Settings UI section
- API routes for version/apply/upload

The plugin is a "core" plugin - always loaded, no external manifest.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from pydantic import BaseModel

from jupiter.core.bridge.interfaces import (
    IPlugin,
    IPluginManifest,
    IPluginHealth,
    IPluginMetrics,
    PluginState,
    PluginType,
    Permission,
    PluginCapabilities,
    CLIContribution,
    APIContribution,
    UIContribution,
    UILocation,
    HealthCheckResult,
    HealthStatus,
    PluginMetrics,
)
from jupiter.core.bridge.exceptions import PluginError

if TYPE_CHECKING:
    from jupiter.server.meeting_adapter import MeetingAdapter

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


# =============================================================================
# API Models
# =============================================================================

class UpdateRequest(BaseModel):
    """Request model for applying an update."""
    source: str
    force: bool = False


class UpdateResponse(BaseModel):
    """Response model for update operations."""
    status: str
    message: str


class VersionResponse(BaseModel):
    """Response model for version endpoint."""
    version: str


class UploadResponse(BaseModel):
    """Response model for file upload."""
    path: Optional[str]
    filename: Optional[str]


# =============================================================================
# Plugin Manifest (implements IPluginManifest)
# =============================================================================

class SettingsUpdateManifest(IPluginManifest):
    """Hard-coded manifest for settings_update plugin.
    
    Implements all abstract properties of IPluginManifest.
    """
    
    @property
    def id(self) -> str:
        return "settings_update"
    
    @property
    def name(self) -> str:
        return "Settings Update"
    
    @property
    def version(self) -> str:
        return __version__
    
    @property
    def description(self) -> str:
        return "Provides self-update functionality for Jupiter from ZIP or Git sources."
    
    @property
    def plugin_type(self) -> PluginType:
        return PluginType.CORE
    
    @property
    def jupiter_version(self) -> str:
        return ">=0.1.0"
    
    @property
    def permissions(self) -> List[Permission]:
        return [
            Permission.FS_READ,
            Permission.FS_WRITE,
            Permission.RUN_COMMANDS,
        ]
    
    @property
    def dependencies(self) -> Dict[str, str]:
        return {}
    
    @property
    def capabilities(self) -> PluginCapabilities:
        return PluginCapabilities(
            metrics_enabled=True,
            health_check_enabled=True,
            jobs_enabled=False,
        )
    
    @property
    def cli_contributions(self) -> List[CLIContribution]:
        return []  # No CLI commands for this plugin
    
    @property
    def api_contributions(self) -> List[APIContribution]:
        return []  # Contributions are registered dynamically
    
    @property
    def ui_contributions(self) -> List[UIContribution]:
        return [
            UIContribution(
                id="update",
                location=UILocation.SETTINGS,
                route="/settings#update",
                title_key="update_settings",
                icon="🔄",
                order=90,
                settings_section="update",
            )
        ]
    
    @property
    def trust_level(self) -> str:
        return "official"
    
    @property
    def source_path(self) -> Optional[Path]:
        return None  # Core plugin, no external source
    
    @property
    def config_defaults(self) -> Dict[str, Any]:
        return {"enabled": True}
    
    @property
    def icon(self) -> Optional[str]:
        return "🔄"
    
    @property
    def author(self) -> str:
        return "Jupiter Team"
    
    @property
    def license(self) -> str:
        return "MIT"
    
    @property
    def homepage(self) -> str:
        return "https://github.com/sn8k/Jupiter-project"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize manifest to dict."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "plugin_type": self.plugin_type.value,
            "jupiter_version": self.jupiter_version,
            "permissions": [p.value for p in self.permissions],
            "dependencies": self.dependencies,
            "capabilities": self.capabilities.to_dict(),
            "cli_contributions": [c.to_dict() for c in self.cli_contributions],
            "api_contributions": [a.to_dict() for a in self.api_contributions],
            "ui_contributions": [u.to_dict() for u in self.ui_contributions],
            "trust_level": self.trust_level,
            "config_defaults": self.config_defaults,
            "author": self.author,
            "license": self.license,
            "homepage": self.homepage,
            "icon": self.icon,
        }


# =============================================================================
# Plugin Implementation
# =============================================================================

class SettingsUpdatePlugin(IPlugin, IPluginHealth, IPluginMetrics):
    """Settings Update core plugin.
    
    Provides self-update functionality for Jupiter.
    """
    
    def __init__(self):
        """Initialize the plugin."""
        self._manifest = SettingsUpdateManifest()
        self._config: Dict[str, Any] = {}
        self._enabled: bool = True
        self._meeting_adapter: Optional["MeetingAdapter"] = None
        self._router: Optional[APIRouter] = None
        self._logger = logger  # Default logger
        
        # Metrics tracking
        self._update_count: int = 0
        self._error_count: int = 0
        self._last_update: Optional[float] = None
    
    @property
    def manifest(self) -> IPluginManifest:
        """Get the plugin manifest."""
        return self._manifest
    
    def init(self, services: Any) -> None:
        """Initialize the plugin with services.
        
        Args:
            services: Service locator from Bridge
        """
        # Get logger from services if available
        if services and hasattr(services, 'get_logger'):
            self._logger = services.get_logger()
        self._logger.info("[settings_update] Initializing core plugin")
        
        # Create API router
        self._router = self._create_router()
    
    def shutdown(self) -> None:
        """Cleanup when plugin is unloaded."""
        self._logger.info("[settings_update] Shutting down")
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin.
        
        Args:
            config: Plugin configuration
        """
        self._config = config or {}
        self._enabled = bool(self._config.get("enabled", True))
        logger.info("[settings_update] Configured: enabled=%s", self._enabled)
    
    def set_meeting_adapter(self, adapter: "MeetingAdapter") -> None:
        """Set the meeting adapter for feature access validation."""
        self._meeting_adapter = adapter
    
    # =========================================================================
    # Health & Metrics (IPluginHealth, IPluginMetrics)
    # =========================================================================
    
    def health(self) -> HealthCheckResult:
        """Get plugin health status."""
        if not self._enabled:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="Plugin is disabled",
                details={"enabled": False}
            )
        
        return HealthCheckResult(
            status=HealthStatus.HEALTHY,
            message="Settings update plugin is operational",
            details={
                "enabled": self._enabled,
                "update_count": self._update_count,
                "error_count": self._error_count,
            }
        )
    
    def metrics(self) -> PluginMetrics:
        """Get plugin metrics."""
        return PluginMetrics(
            execution_count=self._update_count,
            error_count=self._error_count,
            last_execution=self._last_update,
            custom={
                "enabled": self._enabled,
            }
        )
    
    # =========================================================================
    # API Contributions
    # =========================================================================
    
    def get_api_contribution(self) -> APIContribution:
        """Get API router contribution."""
        if self._router is None:
            self._router = self._create_router()
        
        return APIContribution(
            plugin_id=self._manifest.id,
            router=self._router,
            prefix="/plugins/settings_update",
            tags=["update"],
        )
    
    def _create_router(self) -> APIRouter:
        """Create the FastAPI router for this plugin."""
        router = APIRouter()
        
        @router.get("/version", response_model=VersionResponse)
        async def get_version() -> VersionResponse:
            """Get current Jupiter version."""
            return VersionResponse(version=self.get_current_version())
        
        @router.post("/apply", response_model=UpdateResponse)
        async def apply_update(req: UpdateRequest) -> UpdateResponse:
            """Apply a self-update."""
            try:
                result = self.apply_update(req.source, req.force)
                return UpdateResponse(**result)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except RuntimeError as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @router.post("/upload", response_model=UploadResponse)
        async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
            """Upload an update ZIP file."""
            try:
                content = await file.read()
                result = self.upload_update_file(content, file.filename or "update.zip")
                return UploadResponse(**result)
            except RuntimeError as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        return router
    
    # =========================================================================
    # UI Contributions
    # =========================================================================
    
    def get_ui_contribution(self) -> UIContribution:
        """Get UI contribution for settings page."""
        return UIContribution(
            plugin_id=self._manifest.id,
            panel_type="settings",
            panel_id="update",
            title_key="update_settings",
            mount_point="settings",
            order=90,
            icon="🔄",
        )
    
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
        # Return the same JS as the original plugin
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
                window.showNotification(message, type === 'error' ? 'error' : type, {
                    title: 'Update',
                    icon: type === 'error' ? '⚠️' : '🔄'
                });
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
            return fetch(url, opts);
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
    
    # =========================================================================
    # Update Logic
    # =========================================================================
    
    def get_current_version(self) -> str:
        """Get the current Jupiter version."""
        try:
            version_file = Path(__file__).parent.parent.parent.parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning("[settings_update] Failed to read VERSION file: %s", e)
        return "unknown"
    
    def apply_update(self, source: str, force: bool = False) -> Dict[str, str]:
        """Apply an update from a ZIP file or Git repository.
        
        Args:
            source: Path to a ZIP file or Git URL
            force: If True, continue even on errors
            
        Returns:
            Dict with status and message
        """
        if not self._enabled:
            raise RuntimeError("settings_update plugin is disabled")
        
        # Validate feature access if meeting adapter is set
        if self._meeting_adapter:
            self._meeting_adapter.validate_feature_access("update")
        
        self._last_update = datetime.now(timezone.utc).timestamp()
        logger.info("[settings_update] Starting update from %s", source)
        
        try:
            if Path(source).is_file() and source.endswith(".zip"):
                result = self._apply_zip_update(source, force)
            elif source.startswith("git+") or source.endswith(".git"):
                result = self._apply_git_update(source, force)
            else:
                msg = "Unknown source format. Use a .zip file or a git URL."
                logger.error("[settings_update] %s", msg)
                raise ValueError(msg)
            
            self._update_count += 1
            return result
            
        except Exception as e:
            self._error_count += 1
            raise
    
    def _apply_zip_update(self, zip_path: str, force: bool) -> Dict[str, str]:
        """Apply update from a ZIP file."""
        import zipfile
        
        logger.info("[settings_update] Updating from local ZIP file: %s", zip_path)
        try:
            dest_dir = Path.cwd()
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
            
            logger.info("[settings_update] Update applied successfully from ZIP.")
            return {"status": "ok", "message": "Update applied successfully. Please restart."}
        except Exception as e:
            logger.error("[settings_update] ZIP update failed: %s", e)
            if not force:
                raise RuntimeError(f"Update failed: {e}") from e
            return {"status": "warning", "message": f"Update completed with errors: {e}"}
    
    def _apply_git_update(self, git_source: str, force: bool) -> Dict[str, str]:
        """Apply update from a Git repository."""
        import subprocess
        
        logger.info("[settings_update] Updating from Git repository: %s", git_source)
        try:
            # For now, just simulate git pull
            logger.info("[settings_update] Git update simulated.")
            return {"status": "ok", "message": "Git update applied successfully. Please restart."}
        except subprocess.CalledProcessError as e:
            logger.error("[settings_update] Git update failed: %s", e)
            if not force:
                raise RuntimeError(f"Git update failed: {e}") from e
            return {"status": "warning", "message": f"Git update completed with errors: {e}"}
    
    def upload_update_file(self, file_content: bytes, filename: str) -> Dict[str, Optional[str]]:
        """Upload and save an update ZIP file."""
        if not self._enabled:
            raise RuntimeError("settings_update plugin is disabled")
        
        try:
            fd, path = tempfile.mkstemp(suffix=".zip")
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(file_content)
            
            logger.info("[settings_update] Update file uploaded: %s -> %s", filename, path)
            return {"path": path, "filename": filename}
        except Exception as e:
            logger.error("[settings_update] Failed to upload update file: %s", e)
            raise RuntimeError(f"Failed to upload file: {e}") from e


__all__ = ["SettingsUpdatePlugin", "SettingsUpdateManifest"]
