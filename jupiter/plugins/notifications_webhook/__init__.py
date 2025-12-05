"""
Notifications Webhook Plugin v2 - Jupiter Bridge Architecture

This plugin dispatches notifications to a webhook URL or falls back
to local WebSocket notifications in the UI.

Conforme à plugins_architecture.md v0.6.0

@version 1.0.0
@module jupiter.plugins.notifications_webhook
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

__version__ = "1.0.0"

# =============================================================================
# BRIDGE REFERENCES (injected during init)
# =============================================================================

_bridge = None
_logger: Optional[logging.Logger] = None


# =============================================================================
# PLUGIN STATE
# =============================================================================

@dataclass
class PluginState:
    """Internal state of the Notifications Webhook plugin."""
    enabled: bool = True
    url: Optional[str] = None
    events: Set[str] = field(default_factory=lambda: {"scan_complete", "api_connected"})
    timeout: float = 5.0
    retry_count: int = 0
    retry_delay: float = 1.0
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    last_run: Optional[datetime] = None
    notifications_sent: int = 0
    notifications_failed: int = 0
    webhook_calls: int = 0
    local_broadcasts: int = 0
    
    # State tracking
    _last_api_status: Optional[str] = None


_state: Optional[PluginState] = None


def _get_state() -> PluginState:
    """Get or create plugin state."""
    global _state
    if _state is None:
        _state = PluginState()
    return _state


# =============================================================================
# PLUGIN LIFECYCLE (Bridge v2 API)
# =============================================================================

def init(bridge) -> None:
    """
    Initialize the Notifications Webhook plugin.
    
    Args:
        bridge: Instance du Bridge fournissant les registres et services.
    """
    global _bridge, _logger
    _bridge = bridge
    
    # Get dedicated logger via bridge.services (§3.3.1)
    _logger = bridge.services.get_logger("notifications_webhook")
    
    # Load plugin config (merged global + project)
    config = bridge.services.get_config("notifications_webhook") or {}
    
    state = _get_state()
    state.config = config
    state.enabled = config.get("enabled", True)
    state.url = config.get("url") or None
    
    # Parse events
    raw_events = config.get("events")
    if raw_events and isinstance(raw_events, (list, set, tuple)):
        state.events = {str(evt) for evt in raw_events if evt}
    else:
        state.events = {"scan_complete", "api_connected"}
    
    state.timeout = float(config.get("timeout", 5.0))
    state.retry_count = int(config.get("retry_count", 0))
    state.retry_delay = float(config.get("retry_delay", 1.0))
    
    if _logger:
        _logger.info(
            "Notifications Webhook initialized: enabled=%s, url_set=%s, events=%s",
            state.enabled,
            bool(state.url),
            sorted(state.events),
        )


def shutdown() -> None:
    """Shutdown the plugin and cleanup resources."""
    if _logger:
        _logger.info("Notifications Webhook shutting down")


def health() -> Dict[str, Any]:
    """
    Return health status of the plugin.
    
    Returns:
        Dict with status, message, and details.
    """
    state = _get_state()
    
    if not state.enabled:
        return {
            "status": "disabled",
            "message": "Plugin is disabled",
            "details": {"enabled": False},
        }
    
    return {
        "status": "healthy",
        "message": "Notifications Webhook operational",
        "details": {
            "enabled": True,
            "url_configured": bool(state.url),
            "transport": "webhook" if state.url else "local",
            "active_events": sorted(state.events),
        },
    }


def metrics() -> Dict[str, Any]:
    """
    Return plugin metrics.
    
    Returns:
        Dict with notification statistics.
    """
    state = _get_state()
    return {
        "notifications_sent": state.notifications_sent,
        "notifications_failed": state.notifications_failed,
        "webhook_calls": state.webhook_calls,
        "local_broadcasts": state.local_broadcasts,
        "last_run": state.last_run.isoformat() if state.last_run else None,
    }


def reset_settings() -> bool:
    """Reset plugin settings to defaults."""
    global _state
    _state = PluginState()
    if _logger:
        _logger.info("Notifications Webhook settings reset to defaults")
    return True


# =============================================================================
# NOTIFICATION DISPATCH
# =============================================================================

async def _send_webhook(event_alias: str, payload: Dict[str, Any]) -> bool:
    """Send notification via webhook."""
    state = _get_state()
    
    if not state.url:
        if _logger:
            _logger.warning("Webhook URL not configured, skipping")
        return False
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            await client.post(
                state.url,
                json={
                    "event": event_alias,
                    "payload": payload,
                    "timestamp": datetime.now().isoformat(),
                },
                timeout=state.timeout,
            )
        
        state.webhook_calls += 1
        if _logger:
            _logger.info("Webhook sent for event: %s", event_alias)
        return True
        
    except Exception as exc:
        state.notifications_failed += 1
        if _logger:
            _logger.error("Failed to send webhook: %s", exc)
        return False


async def _emit_local_notification(event_alias: str, payload: Dict[str, Any]) -> bool:
    """Emit notification via local WebSocket broadcast."""
    state = _get_state()
    
    try:
        from jupiter.server.ws import manager as ws_manager
    except Exception:
        ws_manager = None
    
    message = payload.get("message") or event_alias
    if _logger:
        _logger.info("Local notification: %s", message)
    
    if not ws_manager:
        return True
    
    try:
        from jupiter.core.events import JupiterEvent, PLUGIN_NOTIFICATION
        
        event_payload = {
            "source": "notifications_webhook",
            "event": event_alias,
            "message": message,
            "details": payload,
        }
        await ws_manager.broadcast(JupiterEvent(type=PLUGIN_NOTIFICATION, payload=event_payload))
        state.local_broadcasts += 1
        return True
        
    except Exception as exc:
        if _logger:
            _logger.warning("Failed to broadcast local notification: %s", exc)
        return False


async def _dispatch_notification(event_alias: str, payload: Dict[str, Any]) -> None:
    """Dispatch notification via appropriate transport."""
    state = _get_state()
    
    if _logger:
        _logger.debug("Dispatching event %s via %s", event_alias, "webhook" if state.url else "local")
    
    success = False
    if state.url:
        success = await _send_webhook(event_alias, payload)
    else:
        success = await _emit_local_notification(event_alias, payload)
    
    if success:
        state.notifications_sent += 1


def _schedule_notification(event_alias: str, payload: Dict[str, Any]) -> None:
    """Schedule an async notification dispatch."""
    state = _get_state()
    
    if not state.enabled:
        if _logger:
            _logger.debug("Plugin disabled; not scheduling %s", event_alias)
        return
    
    if event_alias not in state.events:
        if _logger:
            _logger.debug("Event %s not enabled; skipping", event_alias)
        return
    
    if _logger:
        _logger.debug("Scheduling event %s", event_alias)

    async def runner() -> None:
        await _dispatch_notification(event_alias, payload)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(runner())
    except RuntimeError:
        asyncio.run(runner())


# =============================================================================
# HOOKS (Bridge v2 API)
# =============================================================================

def on_scan(report: Dict[str, Any]) -> None:
    """
    Hook called after scan completion.
    
    Args:
        report: The scan report dict.
    """
    state = _get_state()
    state.last_run = datetime.now()
    
    if not state.enabled:
        if _logger:
            _logger.debug("Plugin disabled; skipping scan hooks")
        return
    
    # Handle scan_complete event
    if "scan_complete" in state.events:
        file_count = len(report.get("files", []))
        summary: Dict[str, Any] = {
            "root": report.get("root"),
            "file_count": file_count,
            "timestamp": report.get("last_scan_timestamp"),
            "message": f"Scan completed ({file_count} files).",
        }
        if not state.url:
            summary["message"] += " Webhook URL not configured; delivered locally."
        
        if _logger:
            _logger.info("Queueing scan_complete notification (%d files)", file_count)
        _schedule_notification("scan_complete", summary)
    
    # Handle api_connected event
    _handle_api_status(report)


def _handle_api_status(report: Dict[str, Any]) -> None:
    """Check and notify API status changes."""
    state = _get_state()
    
    if "api_connected" not in state.events:
        return
    
    api_info = report.get("api") or {}
    api_config = api_info.get("config") or {}
    base_url = api_config.get("base_url")
    
    if not base_url:
        return
    
    endpoints = api_info.get("endpoints") or []
    status = "online" if endpoints else "offline"
    
    if _logger:
        _logger.debug("API status evaluation: %s (endpoints=%d)", status, len(endpoints))
    
    if status == state._last_api_status:
        return
    
    state._last_api_status = status
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
    
    if _logger:
        _logger.info("API status changed -> %s", status)
    _schedule_notification("api_connected", payload)


def on_analyze(summary: Dict[str, Any]) -> None:
    """
    Hook called after analysis.
    
    Args:
        summary: The analysis summary dict.
    """
    # Reserved for future events (analysis_complete, quality_alert)
    pass


# =============================================================================
# PUBLIC API
# =============================================================================

async def run_test() -> Dict[str, Any]:
    """
    Send a synthetic notification to validate transport configuration.
    
    Returns:
        Dict with test result.
    """
    state = _get_state()
    
    if not state.enabled:
        raise RuntimeError("notifications_webhook plugin is disabled")
    
    payload: Dict[str, Any] = {
        "root": state.config.get("root"),
        "timestamp": datetime.now().isoformat(),
        "message": "Test notification triggered from Jupiter settings.",
    }
    
    if _logger:
        _logger.info("Running transport test (webhook=%s)", bool(state.url))
    
    await _dispatch_notification("test_notification", payload)
    
    return {
        "event": "test_notification",
        "transport": "webhook" if state.url else "local",
        "payload": payload,
    }


def configure(config: Dict[str, Any]) -> None:
    """
    Configure the plugin (legacy API).
    
    Args:
        config: Configuration dictionary.
    """
    state = _get_state()
    state.config = config
    state.enabled = config.get("enabled", True)
    state.url = config.get("url") or None
    
    raw_events = config.get("events")
    if raw_events and isinstance(raw_events, (list, set, tuple)):
        state.events = {str(evt) for evt in raw_events if evt}
    else:
        state.events = {"scan_complete", "api_connected"}
    
    state.timeout = float(config.get("timeout", 5.0))
    state.retry_count = int(config.get("retry_count", 0))
    state.retry_delay = float(config.get("retry_delay", 1.0))
    
    if _logger:
        _logger.info(
            "Configured: enabled=%s, url_set=%s, events=%s",
            state.enabled,
            bool(state.url),
            sorted(state.events),
        )


def get_config() -> Dict[str, Any]:
    """Get current plugin configuration."""
    state = _get_state()
    return {
        "enabled": state.enabled,
        "url": state.url,
        "events": list(state.events),
        "timeout": state.timeout,
        "retry_count": state.retry_count,
        "retry_delay": state.retry_delay,
    }


# =============================================================================
# LEGACY COMPATIBILITY - Class-based plugin interface
# =============================================================================

class Plugin:
    """
    Legacy class-based plugin interface for backward compatibility.
    """
    
    name = "notifications_webhook"
    version = __version__
    description = "Sends notifications to a webhook URL or falls back to local events."
    trust_level = "trusted"
    default_events = ("scan_complete", "api_connected")
    
    # UI Configuration
    from jupiter.plugins import PluginUIConfig, PluginUIType
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SETTINGS,
        menu_icon="🔔",
        menu_label_key="notifications_settings",
        menu_order=50,
        view_id="notifications",
    )
    
    def __init__(self) -> None:
        self._state = _get_state()
    
    def configure(self, config: Dict[str, Any]) -> None:
        configure(config)
    
    def hook_on_scan(self, report: Dict[str, Any]) -> None:
        """Compatibility shim for legacy hook naming."""
        on_scan(report)
    
    def on_scan(self, report: Dict[str, Any]) -> None:
        on_scan(report)
    
    def on_analyze(self, summary: Dict[str, Any]) -> None:
        on_analyze(summary)
    
    async def run_test(self) -> Dict[str, Any]:
        return await run_test()
    
    def get_settings_html(self) -> str:
        """Return HTML for legacy settings rendering."""
        from .web.ui import get_settings_html
        return get_settings_html()
    
    def get_settings_js(self) -> str:
        """Return JS for legacy settings rendering."""
        from .web.ui import get_settings_js
        return get_settings_js()
