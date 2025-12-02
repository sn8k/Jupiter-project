# Changelog – jupiter/core/graph.py

## [2025-12-02] – DEPRECATED

**This module is deprecated as of v1.8.0.**

The Live Map functionality has been migrated to a dedicated plugin:
- New location: `jupiter/plugins/livemap.py`
- New API endpoint: `/plugins/livemap/graph`

### Migration Guide
- Replace `from jupiter.core.graph import GraphBuilder` with `from jupiter.plugins.livemap import GraphBuilder`
- Update API calls from `/graph` to `/plugins/livemap/graph`

This file is kept for backwards compatibility and will emit a `DeprecationWarning` on import.
It will be removed in a future version.

---

## Previous History

- Initial implementation of `GraphBuilder`, `GraphNode`, `GraphEdge`, and `DependencyGraph` for Live Map visualization
- Support for detailed mode (file-level nodes) and simplified mode (directory-level nodes)
- Auto-simplification when file count exceeds `max_nodes` threshold
- Import path resolution with fuzzy matching
