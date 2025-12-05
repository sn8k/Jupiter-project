"""
Code Quality Plugin - Bridge v2 Structure
=========================================

Comprehensive code quality analysis with complexity, duplication, and maintainability metrics.

Version: 0.8.1
"""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from jupiter.plugins.code_quality.core.analyzer import CodeQualityAnalyzer

__version__ = "0.8.1"

# Module-level logger (set during init)
_logger: Any = None

# Plugin instance and state
_analyzer: Optional[CodeQualityAnalyzer] = None
_config: dict[str, Any] = {}


def init(bridge) -> bool:
    """
    Initialize the code_quality plugin.
    
    Args:
        bridge: The plugin bridge instance
        
    Returns:
        True if initialization successful
    """
    global _logger, _analyzer
    _logger = bridge.services.get_logger("code_quality")
    
    # Import and create analyzer instance
    from jupiter.plugins.code_quality.core.analyzer import CodeQualityAnalyzer
    _analyzer = CodeQualityAnalyzer()
    
    if _logger:
        _logger.info("Code Quality plugin initialized (v%s)", __version__)
    
    return True


def shutdown() -> None:
    """Clean up plugin resources."""
    global _analyzer, _config
    if _logger:
        _logger.info("Code Quality plugin shutting down")
    _analyzer = None
    _config = {}


def configure(config: dict[str, Any]) -> None:
    """
    Apply configuration to the plugin.
    
    Args:
        config: Plugin configuration dictionary
    """
    global _config
    _config = config.copy()
    
    if _analyzer:
        _analyzer.configure(config)
    
    if _logger:
        _logger.debug("Code Quality configured: enabled=%s, max_files=%s, threshold=%s",
                      config.get("enabled", True),
                      config.get("max_files", 200),
                      config.get("complexity_threshold", 15))


def get_config() -> dict[str, Any]:
    """Return current plugin configuration."""
    if _analyzer:
        return _analyzer.get_config()
    return {
        "enabled": _config.get("enabled", True),
        "max_files": _config.get("max_files", 200),
        "complexity_threshold": _config.get("complexity_threshold", 15),
        "duplication_chunk_size": _config.get("duplication_chunk_size", 6),
        "include_tests": _config.get("include_tests", False),
    }


def on_scan(scan_result: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Hook called after a scan completes.
    
    Args:
        scan_result: The scan result dictionary
        config: Plugin configuration
    """
    if not config.get("enabled", True):
        if _logger:
            _logger.debug("Code Quality disabled; skipping on_scan")
        return
    
    if _analyzer:
        _analyzer.on_scan(scan_result)


def on_analyze(analysis_result: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Hook called after analysis completes.
    
    Args:
        analysis_result: The analysis result dictionary
        config: Plugin configuration
    """
    if not config.get("enabled", True):
        if _logger:
            _logger.debug("Code Quality disabled; skipping on_analyze")
        return
    
    if _analyzer:
        _analyzer.on_analyze(analysis_result)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_last_summary() -> Optional[dict[str, Any]]:
    """
    Get the last computed quality summary.
    
    Returns:
        The summary dictionary or None
    """
    if _analyzer:
        summary = _analyzer.get_last_summary()
        if summary:
            return summary.to_dict()
    return None


def create_manual_link(label: Optional[str], cluster_hashes: list[str]) -> dict[str, Any]:
    """
    Create a manual duplication link.
    
    Args:
        label: Optional label for the link
        cluster_hashes: List of cluster hashes to link
        
    Returns:
        The created cluster dictionary
    """
    if not _analyzer:
        raise ValueError("Plugin not initialized")
    return _analyzer.create_manual_link(label, cluster_hashes)


def delete_manual_link(link_id: str) -> None:
    """
    Delete a manual duplication link.
    
    Args:
        link_id: ID of the link to delete
    """
    if not _analyzer:
        raise ValueError("Plugin not initialized")
    _analyzer.delete_manual_link(link_id)


def recheck_manual_links(link_id: Optional[str] = None) -> dict[str, Any]:
    """
    Re-check manual duplication links.
    
    Args:
        link_id: Optional specific link ID to recheck
        
    Returns:
        Status dictionary with rechecked links
    """
    if not _analyzer:
        raise ValueError("Plugin not initialized")
    return _analyzer.recheck_manual_links(link_id)


# ─────────────────────────────────────────────────────────────────────────────
# UI Methods (Bridge v2)
# ─────────────────────────────────────────────────────────────────────────────

def get_ui_html() -> str:
    """Return HTML content for the Code Quality view."""
    from jupiter.plugins.code_quality.web.ui import get_ui_html as _get_html
    from jupiter.plugins.code_quality.web.ui import get_ui_css as _get_css
    return _get_html() + _get_css()


def get_ui_js() -> str:
    """Return JavaScript code for the Code Quality view."""
    from jupiter.plugins.code_quality.web.ui import get_ui_js as _get_js
    return _get_js()


def get_settings_html() -> str:
    """Return HTML for the settings section."""
    from jupiter.plugins.code_quality.web.ui import get_settings_html as _get_html
    from jupiter.plugins.code_quality.web.ui import get_settings_css as _get_css
    return _get_html() + _get_css()


def get_settings_js() -> str:
    """Return JavaScript for the settings section."""
    from jupiter.plugins.code_quality.web.ui import get_settings_js as _get_js
    return _get_js()
