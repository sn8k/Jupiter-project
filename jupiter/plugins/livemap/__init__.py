"""
Live Map Plugin - Bridge v2 Structure
=====================================

Interactive dependency graph visualization using D3.js.
Features file-level and directory-level dependency graphs.

Version: 0.3.2 - Added API router contribution for /plugins/livemap/graph endpoint
"""

from __future__ import annotations

from typing import Any, Optional

__version__ = "0.3.2"

# Module-level logger (set during init)
_logger: Any = None

# Plugin state
_last_graph: Optional[dict[str, Any]] = None
_config: dict[str, Any] = {}


def init(bridge) -> bool:
    """
    Initialize the livemap plugin.
    
    Args:
        bridge: The plugin bridge instance
        
    Returns:
        True if initialization successful
    """
    global _logger
    _logger = bridge.services.get_logger("livemap")
    
    if _logger:
        _logger.info("Live Map plugin initialized (v%s)", __version__)
    
    return True


def shutdown() -> None:
    """Clean up plugin resources."""
    global _last_graph, _config
    if _logger:
        _logger.info("Live Map plugin shutting down")
    _last_graph = None
    _config = {}


def configure(config: dict[str, Any]) -> None:
    """
    Apply configuration to the plugin.
    
    Args:
        config: Plugin configuration dictionary
    """
    global _config
    _config = config.copy()
    
    if _logger:
        _logger.debug("Live Map configured: enabled=%s, simplify=%s, max_nodes=%s",
                      config.get("enabled", True),
                      config.get("simplify", False),
                      config.get("max_nodes", 1000))


def get_config() -> dict[str, Any]:
    """Return current plugin configuration."""
    return {
        "enabled": _config.get("enabled", True),
        "simplify": _config.get("simplify", False),
        "max_nodes": _config.get("max_nodes", 1000),
        "show_functions": _config.get("show_functions", False),
        "link_distance": _config.get("link_distance", 60),
        "charge_strength": _config.get("charge_strength", -100),
    }


def on_scan(scan_result: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Hook called after a scan completes.
    Pre-builds the dependency graph.
    
    Args:
        scan_result: The scan result dictionary
        config: Plugin configuration
    """
    global _last_graph
    
    if not config.get("enabled", True):
        return
    
    files = scan_result.get("files", [])
    if not files:
        return
    
    try:
        from jupiter.plugins.livemap.core.graph import GraphBuilder
        
        simplify = config.get("simplify", False)
        max_nodes = config.get("max_nodes", 1000)
        
        builder = GraphBuilder(files, simplify=simplify, max_nodes=max_nodes)
        graph = builder.build()
        _last_graph = graph.to_dict()
        
        if _logger:
            _logger.info("Live Map: Built graph with %d nodes, %d links",
                         len(_last_graph.get("nodes", [])),
                         len(_last_graph.get("links", [])))
    except Exception as e:
        if _logger:
            _logger.error("Live Map failed to build graph: %s", e)


def on_analyze(analysis_result: dict[str, Any], config: dict[str, Any]) -> None:
    """
    Hook called after analysis completes.
    
    Args:
        analysis_result: The analysis result dictionary
        config: Plugin configuration
    """
    pass  # No action needed for analysis


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_last_graph() -> Optional[dict[str, Any]]:
    """
    Return the last built graph.
    
    Returns:
        The graph dictionary or None
    """
    return _last_graph


def build_graph(files: list[dict[str, Any]], 
                simplify: bool = False, 
                max_nodes: int = 1000) -> dict[str, Any]:
    """
    Build a new dependency graph from files.
    
    Args:
        files: List of file dictionaries from scan
        simplify: Whether to use simplified mode
        max_nodes: Maximum nodes before auto-simplify
        
    Returns:
        Graph dictionary with nodes and links
    """
    global _last_graph
    
    from jupiter.plugins.livemap.core.graph import GraphBuilder
    
    if _logger:
        _logger.info("Building graph: %d files, simplify=%s, max_nodes=%d",
                     len(files), simplify, max_nodes)
    
    builder = GraphBuilder(files, simplify=simplify, max_nodes=max_nodes)
    graph = builder.build()
    _last_graph = graph.to_dict()
    
    return _last_graph
