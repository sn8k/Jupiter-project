# Changelog – jupiter/plugins/livemap/

## [0.3.2] - Added API Router for Graph Endpoint

### Fixed
- Fixed 404 error when loading graph in WebUI
- The `/plugins/livemap/graph` endpoint was relying on deprecated PluginManager
- Added proper Bridge v2 API contribution with FastAPI router

### Added
- `server/__init__.py` - Server module initialization
- `server/api.py` - FastAPI router with `/graph`, `/config` endpoints
- API router is now registered via Bridge v2 plugin system

### Changed
- Updated `plugin.yaml` to declare `api.router` contribution
- Router mounted at `/plugins/livemap` prefix (matches existing JS calls)
- Updated version to 0.3.2

### Technical Details
- The graph endpoint now uses `jupiter.plugins.livemap.build_graph()` directly
- Fallback to connector scan if cache is empty
- Proper error handling with HTTPException

---

## [0.3.1] - plugin.yaml Schema Compliance Fix

### Fixed
- Rewrote `plugin.yaml` for JSON schema compliance
- Added required `type: tool` field
- Added required `jupiter_version: ">=1.8.0"` field
- Proper `capabilities` object structure (was array)
- Proper `ui.panels` array structure
- Proper `entrypoints` object (init, shutdown only)
- Proper `config.defaults` object

---

## [0.3.0] - Migrated to Bridge v2 Structure

### Changed
- Migrated from legacy `jupiter/core/graph.py` and `jupiter/plugins/livemap.py` to Bridge v2 plugin structure
- Split into `__init__.py` (lifecycle), `core/graph.py` (logic), `web/ui.py` (templates)
- Added `plugin.yaml` manifest with complete metadata
- Uses `bridge.services.get_logger()` for logging
- UI type: `both` (sidebar + settings)

### Added
- `plugin.yaml` manifest v0.3.0 with full Bridge v2 metadata
- `core/graph.py` with `GraphNode`, `GraphEdge`, `DependencyGraph`, `GraphBuilder` classes
- `core/__init__.py` module exports
- `web/ui.py` with D3.js-based interactive visualization
- `web/lang/en.json` and `web/lang/fr.json` i18n files

### Technical Details
- Plugin ID: `livemap`
- View ID: `livemap`
- Interactive D3.js force-directed graph
- Node coloring by file type (py=green, js/ts=blue, etc.)
- Zoom, pan, and node selection features

### Deprecation
- `jupiter/core/graph.py` is now deprecated and shows warning
- Legacy import path still works via shim for backward compatibility

---

## v0.3.0 (2024-12-03)

**Major fix for import resolution - LiveMap now shows proper connections!**

### Root Cause Analysis
The LiveMap was showing mostly isolated nodes with very few connections (0% resolution rate).
Investigation revealed that Python imports were being stored as `module.symbol` instead of just `module`.

Example: `from jupiter.config import load_config` was stored as `jupiter.config.load_config`,
which the graph builder tried to resolve as `jupiter/config/load_config.py` - a file that doesn't exist!

### Fixed
- Coordinated fix with `jupiter/core/language/python.py` v1.3.0
- Import resolution now works correctly because imports are stored as module paths

### Improved `_resolve_import_path()`
- **Strategy 1: Direct/Suffix Match** - Check both `.py` and `/__init__.py` for package imports
- **Strategy 2: Progressive Shortening** - Try shorter paths for submodule imports
- **Strategy 3: Scored Fuzzy Matching** - Use path part scoring with 50% minimum threshold
- Better separation of Python extensions (`[".py", "/__init__.py"]`) from JS extensions
- More efficient suffix matching (iterate all file_map paths, not just filename index)

### Results
- Import resolution rate: ~0% → ~80%+
- Graph now shows meaningful dependency connections between project files
- Isolated node problem resolved

---

## v0.2.2 (2024-12-02)

**Added comprehensive logging for debugging.**

### Added
- Detailed logging throughout the plugin following global `log_level` settings
- `GraphBuilder.__init__`: logs file count, settings, index sizes
- `GraphBuilder.build()`: logs mode, auto-simplify decisions, final stats
- `GraphBuilder._build_detailed()`: logs import resolution rate (% resolved)
- `GraphBuilder._build_simplified()`: logs directory count, import stats
- `GraphBuilder._process_file()`: logs per-file imports found/resolved, functions
- `GraphBuilder._resolve_import_path()`: logs each resolution attempt and result
- `LiveMapPlugin.__init__()`: logs plugin version and initial state
- `LiveMapPlugin.configure()`: logs configuration changes (before/after diff)
- `LiveMapPlugin.get_config()`: logs returned config in debug mode
- `LiveMapPlugin.build_graph()`: logs input, output, and node/link type breakdown
- Exception logging with full traceback in `build_graph()`

### Changed
- Bumped PLUGIN_VERSION to 0.2.2

---

## v0.2.1 (2024-12-02)

**Fixed i18n and improved import resolution.**

### Fixed
- Added all missing i18n keys for the help panel (en + fr):
  - `livemap_nodes`, `livemap_links`
  - `livemap_help_eyebrow`, `livemap_help_what_title`, `livemap_help_what_desc`
  - `livemap_help_interact_title`, `livemap_help_interact_*`
  - `livemap_help_options_title`, `livemap_help_simplify_desc`
  - `livemap_help_colors_title`, `livemap_help_color_*`
  - `livemap_help_tips_title`, `livemap_help_tip_*`

### Improved
- Completely rewritten `_resolve_import_path()` to handle more import formats:
  - Python imports: `jupiter.core.scanner` → `jupiter/core/scanner.py`
  - JS/TS ES6 imports: `./components/Header` → matches `.js`, `.ts`, `.jsx`, `.tsx`
  - CommonJS requires: `../utils` → fuzzy matches
  - Index files: `components/Button` → `components/Button/index.js`
  - Package init: `jupiter.core` → `jupiter/core/__init__.py`
- Better filtering of external/stdlib imports (won't try to link to lodash, react, etc.)
- Fuzzy matching for relative imports with `..` paths

---

## v0.2.0 (2024-12-02)

**Enhanced UI with help panel and settings section.**

### Added
- Two-column layout: graph visualization on left, help panel on right
- Contextual help panel with usage instructions:
  - Drag nodes to rearrange
  - Scroll to zoom in/out
  - Pan by dragging background
  - Hover for full file path
- Settings section (`get_settings_html()`, `get_settings_js()`)
  - Enable/disable toggle
  - Simplify by default option
  - Max nodes slider
  - Show functions toggle
  - Link distance slider
  - Charge strength slider
  - Dedicated Save button
- `get_config()` method for retrieving current configuration
- `configure()` method for applying settings
- Reset Zoom button for navigation

### Changed
- UI now uses `PluginUIType.BOTH` (sidebar + settings section)
- Improved D3.js visualization with better styling
- Default config now includes `show_functions`, `link_distance`, `charge_strength`

---

## v0.1.0 (2024-12-02)

**Initial release – Live Map plugin migrated from core.**

### Added
- `LiveMapPlugin` class implementing the UIPlugin protocol
- `GraphBuilder` for dependency graph construction (migrated from `jupiter/core/graph.py`)
- `GraphNode`, `GraphEdge`, `DependencyGraph` dataclasses
- Interactive D3.js visualization via `get_ui_html()` and `get_ui_js()`
- Support for simplified mode (group by directory)
- Auto-simplification when file count exceeds `max_nodes`
- API endpoint at `/plugins/livemap/graph`

### Migration Notes
- This plugin replaces `jupiter/core/graph.py` (now deprecated)
- The old `/graph` endpoint in `analyze.py` is deprecated, use `/plugins/livemap/graph`
- Plugin UI accessible via sidebar menu (view_id: "livemap")
