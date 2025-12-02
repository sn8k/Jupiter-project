"""Live Map plugin for Jupiter.

This plugin provides interactive dependency graph visualization using D3.js.
Features:
- File dependency graph from imports analysis
- Simplified mode grouping by directory for large projects
- Zoom/pan and drag interactions
- Color-coded nodes by file type

Migrated from jupiter/core/graph.py as of v1.8.0.

Version: 0.3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from jupiter.plugins import PluginUIConfig, PluginUIType

logger = logging.getLogger(__name__)

PLUGIN_VERSION = "0.3.0"


# === Data Classes ===

@dataclass
class GraphNode:
    """A node in the dependency graph."""
    id: str
    type: str  # "file", "module", "function", "directory"
    label: str
    size: int = 0
    complexity: int = 0
    group: Optional[str] = None


@dataclass
class GraphEdge:
    """An edge in the dependency graph."""
    source: str
    target: str
    type: str  # "import", "call", "contains", "dependency"
    weight: int = 1


@dataclass
class DependencyGraph:
    """Container for the dependency graph."""
    nodes: List[GraphNode] = field(default_factory=list)
    links: List[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [asdict(n) for n in self.nodes],
            "links": [asdict(l) for l in self.links]
        }


class GraphBuilder:
    """Builds a dependency graph from scan results."""

    def __init__(self, files: List[Dict[str, Any]], simplify: bool = False, max_nodes: int = 1000):
        self.files = files
        self.simplify = simplify
        self.max_nodes = max_nodes
        self.nodes: Dict[str, GraphNode] = {}
        self.links: List[GraphEdge] = []
        
        logger.debug(
            "GraphBuilder initialized: %d files, simplify=%s, max_nodes=%d",
            len(files), simplify, max_nodes
        )
        
        # Optimization: Build a lookup map for faster import resolution
        self.file_map: Dict[str, str] = {}
        self.filename_index: Dict[str, List[str]] = {}
        
        for f in self.files:
            path = f["path"].replace("\\", "/")
            self.file_map[path] = path
            
            filename = path.split("/")[-1]
            if filename not in self.filename_index:
                self.filename_index[filename] = []
            self.filename_index[filename].append(path)
        
        logger.debug(
            "File index built: %d unique paths, %d unique filenames",
            len(self.file_map), len(self.filename_index)
        )

    def build(self) -> DependencyGraph:
        """Build and return the dependency graph."""
        logger.info("Building dependency graph (simplify=%s, files=%d)", self.simplify, len(self.files))
        
        # Auto-simplify if too many files
        if not self.simplify and len(self.files) > self.max_nodes:
            logger.info(
                "Auto-enabling simplified mode: %d files exceeds max_nodes=%d",
                len(self.files), self.max_nodes
            )
            self.simplify = True

        if self.simplify:
            self._build_simplified()
        else:
            self._build_detailed()
        
        # Filter links to only include those where both source and target exist
        initial_link_count = len(self.links)
        valid_links = [
            link for link in self.links
            if link.source in self.nodes and link.target in self.nodes
        ]
        
        if initial_link_count != len(valid_links):
            logger.debug(
                "Filtered %d invalid links (source/target not found)",
                initial_link_count - len(valid_links)
            )
        
        graph = DependencyGraph(
            nodes=list(self.nodes.values()),
            links=valid_links
        )
        
        logger.info(
            "Graph built: %d nodes, %d links",
            len(graph.nodes), len(graph.links)
        )
        
        return graph

    def _build_detailed(self) -> None:
        """Build detailed graph with file-level nodes."""
        logger.debug("Building detailed graph (file-level nodes)")
        processed = 0
        imports_found = 0
        imports_resolved = 0
        
        for file in self.files:
            result = self._process_file(file)
            processed += 1
            imports_found += result.get("imports_found", 0)
            imports_resolved += result.get("imports_resolved", 0)
        
        logger.debug(
            "Detailed build complete: %d files processed, %d imports found, %d resolved (%d%% resolution rate)",
            processed, imports_found, imports_resolved,
            int(imports_resolved / imports_found * 100) if imports_found > 0 else 0
        )

    def _build_simplified(self) -> None:
        """Build simplified graph grouped by directory."""
        logger.debug("Building simplified graph (directory-level nodes)")
        
        dir_sizes: Dict[str, int] = {}
        file_to_dir: Dict[str, str] = {}
        
        for file in self.files:
            path = file["path"].replace("\\", "/")
            parent_dir = str(Path(path).parent).replace("\\", "/")
            if parent_dir == ".":
                parent_dir = "root"
            
            dir_sizes[parent_dir] = dir_sizes.get(parent_dir, 0) + file.get("size_bytes", 0)
            file_to_dir[path] = parent_dir

        # Create directory nodes
        for dir_path, size in dir_sizes.items():
            self.nodes[dir_path] = GraphNode(
                id=dir_path,
                type="directory",
                label=dir_path,
                size=size,
                group="directory"
            )
        
        logger.debug("Created %d directory nodes", len(dir_sizes))

        # Create edges between directories
        edges: Set[Tuple[str, str]] = set()
        imports_found = 0
        imports_resolved = 0

        for file in self.files:
            source_path = file["path"].replace("\\", "/")
            source_dir = file_to_dir[source_path]
            
            lang_analysis = file.get("language_analysis") or {}
            imports = lang_analysis.get("imports", [])
            imports_found += len(imports)
            
            for imp in imports:
                target_path = self._resolve_import_path(imp)
                if target_path and target_path in file_to_dir:
                    imports_resolved += 1
                    target_dir = file_to_dir[target_path]
                    if source_dir != target_dir:
                        edges.add((source_dir, target_dir))

        for src, tgt in edges:
            self.links.append(GraphEdge(
                source=src,
                target=tgt,
                type="dependency"
            ))
        
        logger.debug(
            "Simplified build: %d imports found, %d resolved, %d unique directory edges",
            imports_found, imports_resolved, len(edges)
        )

    def _process_file(self, file: Dict[str, Any]) -> Dict[str, int]:
        """Process a single file and add nodes/edges. Returns stats."""
        path = file["path"].replace("\\", "/")
        file_id = path
        
        file_type = file.get("file_type", "")
        group = "file"
        if file_type in ("js", "ts", "jsx", "tsx"):
            group = "js_file"
        elif file_type == "py":
            group = "py_file"

        # Add file node
        self.nodes[file_id] = GraphNode(
            id=file_id,
            type="file",
            label=path.split("/")[-1],
            size=file.get("size_bytes", 0),
            group=group
        )

        lang_analysis = file.get("language_analysis") or {}
        
        # Process imports (edges)
        imports = lang_analysis.get("imports", [])
        imports_found = len(imports)
        imports_resolved = 0
        
        for imp in imports:
            target_path = self._resolve_import_path(imp)
            if target_path and target_path in self.file_map:
                imports_resolved += 1
                self.links.append(GraphEdge(
                    source=file_id,
                    target=target_path,
                    type="import"
                ))
                logger.debug("  Link: %s -> %s (import '%s')", file_id, target_path, imp)
            else:
                logger.debug("  Unresolved import: '%s' in %s", imp, file_id)

        # Process functions (nodes)
        functions = lang_analysis.get("defined_functions", [])
        for func in functions:
            func_id = f"{file_id}::{func}"
            self.nodes[func_id] = GraphNode(
                id=func_id,
                type="function",
                label=func,
                group="function"
            )
            # Link function to file
            self.links.append(GraphEdge(
                source=file_id,
                target=func_id,
                type="contains"
            ))
        
        if imports_found > 0:
            logger.debug(
                "Processed %s: %d imports (%d resolved), %d functions",
                path, imports_found, imports_resolved, len(functions)
            )
        
        return {"imports_found": imports_found, "imports_resolved": imports_resolved}

    def _resolve_import_path(self, import_name: str) -> Optional[str]:
        """Resolve import name to file path.
        
        Handles:
        - Python imports: 'jupiter.core.scanner' -> 'jupiter/core/scanner.py'
        - JS/TS relative imports: './utils' -> 'utils.js' or 'utils/index.js'
        - Package imports: 'lodash' -> may not resolve (external package)
        
        Resolution strategy for Python imports:
        1. Convert dots to slashes: jupiter.core.scanner -> jupiter/core/scanner
        2. Try as a module file: jupiter/core/scanner.py
        3. Try as a package: jupiter/core/scanner/__init__.py
        4. Try progressively shorter paths (in case of submodule imports)
        """
        if not import_name:
            logger.debug("    _resolve: empty import name")
            return None
            
        # Skip external/stdlib packages (heuristic: single word, no dots, no path separators)
        if "." not in import_name and "/" not in import_name and "\\" not in import_name:
            # Could be a stdlib or external package - skip unless it's in our file list
            for ext in (".py", ".js", ".ts", ".jsx", ".tsx"):
                if import_name + ext in self.file_map:
                    logger.debug("    _resolve: '%s' -> direct file match '%s'", import_name, import_name + ext)
                    return self.file_map[import_name + ext]
            logger.debug("    _resolve: '%s' -> skipped (looks like external/stdlib)", import_name)
            return None
        
        # Normalize path separators
        normalized = import_name.replace("\\", "/").replace(".", "/")
        
        # Remove leading ./ for relative imports
        if normalized.startswith("/"):
            normalized = normalized[1:]
        
        # For Python imports, try multiple resolution strategies
        
        # Strategy 1: Try exact module file match (jupiter/core/scanner.py)
        py_extensions = [".py", "/__init__.py"]
        js_extensions = [".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]
        
        for ext in py_extensions + js_extensions:
            path_candidate = normalized + ext
            
            # Direct match in file_map
            if path_candidate in self.file_map:
                logger.debug("    _resolve: '%s' -> direct match '%s'", import_name, path_candidate)
                return self.file_map[path_candidate]
            
            # Suffix match: look for files ending with this path
            # This handles cases where file_map has full paths like "c:/project/jupiter/core/scanner.py"
            for full_path in self.file_map:
                if full_path.endswith(path_candidate) or full_path.endswith("/" + path_candidate):
                    logger.debug("    _resolve: '%s' -> suffix match '%s'", import_name, full_path)
                    return full_path
        
        # Strategy 2: Try progressively shorter paths (for submodule imports)
        # e.g., jupiter.core.scanner.ScanResult might resolve to jupiter/core/scanner.py
        parts = normalized.split("/")
        while len(parts) > 1:
            partial_path = "/".join(parts)
            for ext in py_extensions + js_extensions:
                path_candidate = partial_path + ext
                
                if path_candidate in self.file_map:
                    logger.debug("    _resolve: '%s' -> partial match '%s'", import_name, path_candidate)
                    return self.file_map[path_candidate]
                
                for full_path in self.file_map:
                    if full_path.endswith(path_candidate) or full_path.endswith("/" + path_candidate):
                        logger.debug("    _resolve: '%s' -> partial suffix match '%s'", import_name, full_path)
                        return full_path
            
            parts = parts[:-1]
        
        # Strategy 3: Fuzzy match on filename with directory context
        target_name = normalized.split("/")[-1] if "/" in normalized else normalized
        for ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
            candidates = self.filename_index.get(target_name + ext, [])
            
            # Score candidates by how many path parts they share
            parts = normalized.split("/")
            best_match = None
            best_score = 0
            
            for path in candidates:
                path_lower = path.lower()
                score = sum(1 for part in parts if part and part.lower() in path_lower and part != "..")
                if score > best_score:
                    best_score = score
                    best_match = path
            
            if best_match and best_score >= len(parts) * 0.5:  # At least 50% match
                logger.debug("    _resolve: '%s' -> fuzzy match '%s' (score=%d/%d)", 
                           import_name, best_match, best_score, len(parts))
                return best_match
        
        logger.debug("    _resolve: '%s' -> no match found", import_name)
        return None


class LiveMapPlugin:
    """Live Map visualization plugin for Jupiter.
    
    Provides interactive D3.js-based dependency graph visualization.
    """

    name = "livemap"
    version = PLUGIN_VERSION
    description = "Interactive dependency graph visualization (Live Map)."
    trust_level = "stable"
    
    # UI Configuration - shows in sidebar AND settings
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.BOTH,
        menu_icon="🗺️",
        menu_label_key="livemap_view",
        menu_order=45,  # After Overview (40), before Functions (50)
        view_id="livemap",
        settings_section="Live Map",
    )

    def __init__(self) -> None:
        logger.debug("LiveMapPlugin.__init__() called")
        self.enabled = True
        self.simplify = False
        self.max_nodes = 1000
        self.show_functions = False
        self.link_distance = 60
        self.charge_strength = -100
        self._last_graph: Optional[DependencyGraph] = None
        self._project_root: Optional[Path] = None
        logger.info("LiveMapPlugin v%s initialized (enabled=%s)", PLUGIN_VERSION, self.enabled)

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the plugin."""
        logger.debug("LiveMapPlugin.configure() called with: %s", config)
        old_config = self.get_config()
        
        self.enabled = config.get("enabled", True)
        self.simplify = config.get("simplify", False)
        self.max_nodes = config.get("max_nodes", 1000)
        self.show_functions = config.get("show_functions", False)
        self.link_distance = config.get("link_distance", 60)
        self.charge_strength = config.get("charge_strength", -100)
        
        new_config = self.get_config()
        
        # Log what changed
        changes = []
        for key in new_config:
            if old_config.get(key) != new_config.get(key):
                changes.append(f"{key}: {old_config.get(key)} -> {new_config.get(key)}")
        
        if changes:
            logger.info("LiveMapPlugin configuration changed: %s", ", ".join(changes))
        else:
            logger.debug("LiveMapPlugin configuration unchanged")

    def get_config(self) -> Dict[str, Any]:
        """Return current plugin configuration."""
        config = {
            "enabled": self.enabled,
            "simplify": self.simplify,
            "max_nodes": self.max_nodes,
            "show_functions": self.show_functions,
            "link_distance": self.link_distance,
            "charge_strength": self.charge_strength,
        }
        logger.debug("LiveMapPlugin.get_config() -> %s", config)
        return config

    def on_scan(self, report: Dict[str, Any]) -> None:
        """Hook called after scan - pre-build the graph."""
        logger.debug("LiveMapPlugin.on_scan() called, enabled=%s", self.enabled)
        if not self.enabled:
            logger.debug("LiveMapPlugin disabled, skipping on_scan")
            return
        
        files = report.get("files", [])
        if not files:
            return
            
        try:
            builder = GraphBuilder(files, simplify=self.simplify, max_nodes=self.max_nodes)
            self._last_graph = builder.build()
            logger.debug("LiveMap: Built graph with %d nodes, %d links",
                        len(self._last_graph.nodes), len(self._last_graph.links))
        except Exception as e:
            logger.error("LiveMapPlugin failed to build graph: %s", e)

    def on_analyze(self, summary: Dict[str, Any]) -> None:
        """Hook called after analysis - no-op for now."""
        pass

    def get_last_graph(self) -> Optional[DependencyGraph]:
        """Return the last built graph."""
        logger.debug("LiveMapPlugin.get_last_graph() called, has_graph=%s", self._last_graph is not None)
        return self._last_graph

    def build_graph(self, files: List[Dict[str, Any]], simplify: bool = False, max_nodes: int = 1000) -> DependencyGraph:
        """Build a new graph from files."""
        logger.info(
            "LiveMapPlugin.build_graph() called: %d files, simplify=%s, max_nodes=%d",
            len(files), simplify, max_nodes
        )
        
        try:
            builder = GraphBuilder(files, simplify=simplify, max_nodes=max_nodes)
            graph = builder.build()
            self._last_graph = graph
            
            logger.info(
                "LiveMapPlugin graph built successfully: %d nodes, %d links",
                len(graph.nodes), len(graph.links)
            )
            
            # Log some statistics in debug mode
            if logger.isEnabledFor(logging.DEBUG):
                node_types = {}
                for node in graph.nodes:
                    node_types[node.type] = node_types.get(node.type, 0) + 1
                logger.debug("Node types: %s", node_types)
                
                link_types = {}
                for link in graph.links:
                    link_types[link.type] = link_types.get(link.type, 0) + 1
                logger.debug("Link types: %s", link_types)
            
            return graph
            
        except Exception as e:
            logger.error("LiveMapPlugin.build_graph() failed: %s", e, exc_info=True)
            raise

    # === UI Methods ===
    
    def get_ui_html(self) -> str:
        """Return HTML content for the Live Map view."""
        return """
<div id="livemap-view" class="plugin-view-content">
    <div class="livemap-layout">
        <!-- Main Graph Panel -->
        <section class="livemap-main panel">
            <header>
                <div>
                    <p class="eyebrow" data-i18n="livemap_eyebrow">Visualization</p>
                    <h2 data-i18n="livemap_title">Live Map</h2>
                    <p class="muted" data-i18n="livemap_subtitle">Interactive dependency graph.</p>
                </div>
                <div class="actions">
                    <label class="checkbox-label livemap-option">
                        <input type="checkbox" id="livemap-simplify">
                        <span data-i18n="livemap_simplify">Simplify</span>
                    </label>
                    <button class="btn btn-secondary" id="livemap-reset-zoom" data-i18n="livemap_reset_zoom">Reset Zoom</button>
                    <button class="btn btn-primary" id="livemap-refresh-btn" data-i18n="refresh">Refresh</button>
                </div>
            </header>
            
            <div id="livemap-container" class="livemap-graph-container">
                <div class="livemap-loading" data-i18n="livemap_loading">Loading graph...</div>
            </div>
            
            <footer class="livemap-footer">
                <div id="livemap-stats" class="livemap-stats">
                    <span class="stat-item"><strong id="livemap-node-count">--</strong> <span data-i18n="livemap_nodes">nodes</span></span>
                    <span class="stat-item"><strong id="livemap-link-count">--</strong> <span data-i18n="livemap_links">links</span></span>
                </div>
                <div class="livemap-legend">
                    <span class="legend-item"><span class="legend-dot py"></span> Python</span>
                    <span class="legend-item"><span class="legend-dot js"></span> JS/TS</span>
                    <span class="legend-item"><span class="legend-dot dir"></span> Directory</span>
                    <span class="legend-item"><span class="legend-dot other"></span> Other</span>
                </div>
            </footer>
        </section>
        
        <!-- Help Panel -->
        <aside class="livemap-help panel">
            <header>
                <div>
                    <p class="eyebrow" data-i18n="livemap_help_eyebrow">Guide</p>
                    <h3 data-i18n="livemap_help_title">How to use Live Map</h3>
                </div>
            </header>
            
            <div class="help-content">
                <section class="help-section">
                    <h4 data-i18n="livemap_help_what_title">📊 What is Live Map?</h4>
                    <p class="muted small" data-i18n="livemap_help_what_desc">
                        Live Map visualizes the dependency graph of your project. Each node represents a file 
                        or module, and edges show import relationships between them.
                    </p>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_interact_title">🖱️ Interactions</h4>
                    <ul class="help-list">
                        <li data-i18n="livemap_help_interact_zoom">Scroll to zoom in/out</li>
                        <li data-i18n="livemap_help_interact_pan">Drag background to pan</li>
                        <li data-i18n="livemap_help_interact_drag">Drag nodes to reposition them</li>
                        <li data-i18n="livemap_help_interact_hover">Hover a node to see its name</li>
                    </ul>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_options_title">⚙️ Options</h4>
                    <ul class="help-list">
                        <li><strong data-i18n="livemap_simplify">Simplify</strong>: <span class="muted" data-i18n="livemap_help_simplify_desc">Groups files by folder to reduce clutter on large projects.</span></li>
                    </ul>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_colors_title">🎨 Color Legend</h4>
                    <ul class="help-list color-legend">
                        <li><span class="legend-dot py"></span> <span data-i18n="livemap_help_color_py">Python files (.py)</span></li>
                        <li><span class="legend-dot js"></span> <span data-i18n="livemap_help_color_js">JavaScript/TypeScript files</span></li>
                        <li><span class="legend-dot dir"></span> <span data-i18n="livemap_help_color_dir">Directories (simplified mode)</span></li>
                        <li><span class="legend-dot other"></span> <span data-i18n="livemap_help_color_other">Other files</span></li>
                    </ul>
                </section>
                
                <section class="help-section">
                    <h4 data-i18n="livemap_help_tips_title">💡 Tips</h4>
                    <ul class="help-list">
                        <li data-i18n="livemap_help_tip_scan">Run a scan first to populate the graph</li>
                        <li data-i18n="livemap_help_tip_large">For projects with 1000+ files, Simplify mode is auto-enabled</li>
                        <li data-i18n="livemap_help_tip_settings">Configure defaults in Settings > Plugins > Live Map</li>
                    </ul>
                </section>
            </div>
        </aside>
    </div>
</div>

<style>
#livemap-view {
    height: 100%;
    overflow: hidden;
}

.livemap-layout {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 1rem;
    height: 100%;
    min-height: 600px;
}

@media (max-width: 1200px) {
    .livemap-layout {
        grid-template-columns: 1fr;
        grid-template-rows: 1fr auto;
    }
    .livemap-help {
        max-height: 300px;
        overflow-y: auto;
    }
}

.livemap-main {
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.livemap-main header {
    flex-shrink: 0;
}

.livemap-graph-container {
    flex: 1;
    min-height: 400px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg-subtle);
    overflow: hidden;
    position: relative;
}

.livemap-graph-container svg {
    width: 100%;
    height: 100%;
}

.livemap-loading {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: var(--fg-muted);
    font-size: 0.9rem;
}

.livemap-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.livemap-stats {
    display: flex;
    gap: 1.5rem;
    font-size: 0.85rem;
}

.stat-item {
    color: var(--fg-muted);
}

.stat-item strong {
    color: var(--fg);
}

.livemap-legend {
    display: flex;
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--fg-muted);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.legend-dot.py { background: #3572A5; }
.legend-dot.js { background: #f1e05a; }
.legend-dot.dir { background: #6a5acd; }
.legend-dot.other { background: #69b3a2; }

.livemap-option {
    margin-right: 1rem;
    font-size: 0.85rem;
}

/* Help Panel */
.livemap-help {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
}

.livemap-help header {
    flex-shrink: 0;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.75rem;
    margin-bottom: 0.75rem;
}

.help-content {
    flex: 1;
    overflow-y: auto;
}

.help-section {
    margin-bottom: 1.25rem;
}

.help-section h4 {
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
    color: var(--fg);
}

.help-section p {
    line-height: 1.5;
}

.help-list {
    list-style: none;
    padding: 0;
    margin: 0;
}

.help-list li {
    padding: 0.35rem 0;
    font-size: 0.85rem;
    color: var(--fg-muted);
    border-bottom: 1px solid var(--border-subtle, var(--border));
}

.help-list li:last-child {
    border-bottom: none;
}

.help-list.color-legend li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Graph node colors */
.livemap-node-py { fill: #3572A5; }
.livemap-node-js { fill: #f1e05a; }
.livemap-node-dir { fill: #6a5acd; }
.livemap-node-other { fill: #69b3a2; }

.livemap-link {
    stroke: #999;
    stroke-opacity: 0.6;
}
</style>
"""

    def get_ui_js(self) -> str:
        """Return JavaScript for the Live Map view."""
        return """
(function() {
    const livemapPlugin = {
        simulation: null,
        svg: null,
        g: null,
        zoom: null,
        
        getApiBaseUrl() {
            if (window.state?.apiBaseUrl) return state.apiBaseUrl;
            const origin = window.location?.origin || '';
            if (origin.includes(':8050')) return origin.replace(':8050', ':8000');
            return origin || 'http://127.0.0.1:8000';
        },
        
        getToken() {
            if (window.state?.token) return state.token;
            return localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        },
        
        buildOptions(options = {}) {
            const opts = { ...options };
            const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
            const token = this.getToken();
            if (token && !headers.Authorization) {
                headers.Authorization = `Bearer ${token}`;
            }
            opts.headers = headers;
            return opts;
        },
        
        async request(path, options = {}) {
            const url = path.startsWith('http') ? path : `${this.getApiBaseUrl()}${path}`;
            return fetch(url, this.buildOptions(options));
        },
        
        notify(message, type = 'info') {
            if (typeof window.showNotification === 'function') {
                window.showNotification(message, type, { title: 'Live Map', icon: '🗺️' });
            } else {
                console.log('[LiveMap]', message);
            }
        },
        
        async refresh() {
            const container = document.getElementById('livemap-container');
            if (!container) return;
            
            container.innerHTML = '<div class="livemap-loading">Loading graph...</div>';
            
            const simplify = document.getElementById('livemap-simplify')?.checked || false;
            
            try {
                const response = await this.request(`/plugins/livemap/graph?simplify=${simplify}`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const graphData = await response.json();
                this.render(graphData);
            } catch (err) {
                console.error('[LiveMap] Failed to load graph:', err);
                container.innerHTML = `<div class="livemap-loading" style="color: var(--error);">Error: ${err.message}</div>`;
                this.notify('Failed to load graph: ' + err.message, 'error');
            }
        },
        
        resetZoom() {
            if (this.svg && this.zoom) {
                this.svg.transition().duration(500).call(this.zoom.transform, d3.zoomIdentity);
            }
        },
        
        render(graphData) {
            const container = document.getElementById('livemap-container');
            if (!container) return;
            
            container.innerHTML = '';
            
            if (!graphData.nodes || graphData.nodes.length === 0) {
                container.innerHTML = '<div class="livemap-loading">No graph data. Run a scan first.</div>';
                this.updateStats(0, 0);
                return;
            }
            
            this.updateStats(graphData.nodes.length, graphData.links.length);
            
            if (typeof d3 === 'undefined') {
                container.innerHTML = '<div class="livemap-loading" style="color: var(--error);">D3.js not loaded</div>';
                return;
            }
            
            const width = container.clientWidth || 800;
            const height = container.clientHeight || 600;
            
            this.svg = d3.select('#livemap-container').append('svg')
                .attr('width', width)
                .attr('height', height)
                .attr('viewBox', [0, 0, width, height]);
            
            this.g = this.svg.append('g');
            
            // Zoom behavior
            this.zoom = d3.zoom()
                .extent([[0, 0], [width, height]])
                .scaleExtent([0.1, 8])
                .on('zoom', ({transform}) => this.g.attr('transform', transform));
            
            this.svg.call(this.zoom);
            
            // Simulation
            this.simulation = d3.forceSimulation(graphData.nodes)
                .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(60))
                .force('charge', d3.forceManyBody().strength(-100))
                .force('collide', d3.forceCollide().radius(15))
                .force('center', d3.forceCenter(width / 2, height / 2));
            
            // Links
            const link = this.g.append('g')
                .attr('class', 'links')
                .selectAll('line')
                .data(graphData.links)
                .join('line')
                .attr('class', 'livemap-link')
                .attr('stroke-width', d => Math.sqrt(d.weight || 1));
            
            // Nodes
            const node = this.g.append('g')
                .attr('class', 'nodes')
                .selectAll('circle')
                .data(graphData.nodes)
                .join('circle')
                .attr('r', d => d.type === 'directory' ? 8 : 5)
                .attr('fill', d => this.getNodeColor(d))
                .attr('stroke', '#fff')
                .attr('stroke-width', 1.5)
                .call(this.drag(this.simulation));
            
            node.append('title').text(d => d.label);
            
            this.simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
            });
        },
        
        updateStats(nodes, links) {
            const nodeEl = document.getElementById('livemap-node-count');
            const linkEl = document.getElementById('livemap-link-count');
            if (nodeEl) nodeEl.textContent = nodes;
            if (linkEl) linkEl.textContent = links;
        },
        
        getNodeColor(d) {
            switch (d.group) {
                case 'py_file': return '#3572A5';
                case 'js_file': return '#f1e05a';
                case 'function': return '#ff7f0e';
                case 'directory': return '#6a5acd';
                default: return '#69b3a2';
            }
        },
        
        drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            
            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        },
        
        bind() {
            document.getElementById('livemap-refresh-btn')?.addEventListener('click', () => this.refresh());
            document.getElementById('livemap-reset-zoom')?.addEventListener('click', () => this.resetZoom());
        },
        
        init() {
            this.bind();
            this.refresh();
        }
    };
    
    // Expose globally
    window.livemapPlugin = livemapPlugin;
    window.livemapRefresh = () => livemapPlugin.refresh();
    
    // Initialize when DOM ready or immediately
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => livemapPlugin.init());
    } else {
        livemapPlugin.init();
    }
})();
"""

    def get_settings_html(self) -> str:
        """Return HTML for the settings section."""
        return """
<section class="plugin-settings livemap-settings" id="livemap-settings">
    <header class="plugin-settings-header">
        <div>
            <p class="eyebrow">🗺️ Live Map</p>
            <h3 data-i18n="livemap_settings_title">Live Map Settings</h3>
            <p class="muted small" data-i18n="livemap_settings_hint">Configure the dependency graph visualization defaults.</p>
        </div>
        <label class="toggle-setting">
            <input type="checkbox" id="livemap-enabled" checked>
            <span data-i18n="livemap_enabled">Enable Live Map</span>
        </label>
    </header>
    <div class="settings-grid livemap-grid">
        <div class="setting-item">
            <label for="livemap-max-nodes" data-i18n="livemap_max_nodes">Max Nodes Before Simplify</label>
            <input type="number" id="livemap-max-nodes" value="1000" min="100" max="5000" step="100">
            <p class="setting-hint" data-i18n="livemap_max_nodes_hint">When file count exceeds this, simplified mode is auto-enabled.</p>
        </div>
        <div class="setting-item">
            <label for="livemap-link-distance" data-i18n="livemap_link_distance">Link Distance</label>
            <input type="number" id="livemap-link-distance" value="60" min="20" max="200" step="10">
            <p class="setting-hint" data-i18n="livemap_link_distance_hint">Distance between linked nodes. Higher = more spread out.</p>
        </div>
        <div class="setting-item">
            <label for="livemap-charge-strength" data-i18n="livemap_charge_strength">Charge Strength</label>
            <input type="number" id="livemap-charge-strength" value="-100" min="-500" max="-10" step="10">
            <p class="setting-hint" data-i18n="livemap_charge_strength_hint">Node repulsion force. More negative = more spread.</p>
        </div>
        <div class="setting-item">
            <label class="checkbox-label" for="livemap-default-simplify">
                <input type="checkbox" id="livemap-default-simplify">
                <span data-i18n="livemap_default_simplify">Simplify by Default</span>
            </label>
            <p class="setting-hint" data-i18n="livemap_default_simplify_hint">Start in simplified mode (group by folder).</p>
        </div>
        <div class="setting-item">
            <label class="checkbox-label" for="livemap-show-functions">
                <input type="checkbox" id="livemap-show-functions">
                <span data-i18n="livemap_show_functions">Show Functions as Nodes</span>
            </label>
            <p class="setting-hint" data-i18n="livemap_show_functions_hint">Include function nodes in the graph (can be slow for large projects).</p>
        </div>
    </div>
    <footer class="plugin-settings-footer">
        <button class="btn btn-primary" id="livemap-save-btn" data-i18n="save">Save</button>
        <span class="setting-result" id="livemap-settings-status">&nbsp;</span>
    </footer>
</section>

<style>
#livemap-settings .livemap-grid {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}
#livemap-settings .setting-item {
    border: 1px solid var(--border);
    background: var(--panel-contrast);
    padding: 0.75rem;
    border-radius: var(--radius);
}
#livemap-settings .setting-item label {
    font-weight: 500;
    margin-bottom: 0.5rem;
    display: block;
}
#livemap-settings .setting-item input[type="number"] {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--bg);
    color: var(--fg);
}
#livemap-settings .setting-hint {
    font-size: 0.75rem;
    color: var(--fg-muted);
    margin-top: 0.25rem;
}
#livemap-settings .setting-result {
    min-width: 2rem;
    text-align: center;
}
</style>
"""

    def get_settings_js(self) -> str:
        """Return JavaScript for the settings section."""
        return """
(function() {
    const livemapSettings = {
        getApiBaseUrl() {
            if (window.state?.apiBaseUrl) return state.apiBaseUrl;
            const origin = window.location?.origin || '';
            if (origin.includes(':8050')) return origin.replace(':8050', ':8000');
            return origin || 'http://127.0.0.1:8000';
        },
        
        getToken() {
            if (window.state?.token) return state.token;
            return localStorage.getItem('jupiter-token') || sessionStorage.getItem('jupiter-token');
        },
        
        notify(message, type = 'info') {
            if (typeof window.showNotification === 'function') {
                window.showNotification(message, type, { title: 'Live Map', icon: '🗺️' });
            } else {
                console.log('[LiveMap Settings]', message);
            }
        },
        
        buildOptions(options = {}) {
            const opts = { ...options };
            const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
            const token = this.getToken();
            if (token && !headers.Authorization) {
                headers.Authorization = `Bearer ${token}`;
            }
            if (opts.body && typeof opts.body !== 'string') {
                headers['Content-Type'] = 'application/json';
                opts.body = JSON.stringify(opts.body);
            }
            opts.headers = headers;
            return opts;
        },
        
        async request(path, options = {}) {
            const url = path.startsWith('http') ? path : `${this.getApiBaseUrl()}${path}`;
            return fetch(url, this.buildOptions(options));
        },
        
        setStatus(text = '', variant = null) {
            const statusEl = document.getElementById('livemap-settings-status');
            if (!statusEl) return;
            statusEl.textContent = text;
            statusEl.className = 'setting-result';
            if (variant === 'error') statusEl.style.color = 'var(--error)';
            else if (variant === 'success') statusEl.style.color = 'var(--success)';
            else statusEl.style.color = '';
        },
        
        readPayload() {
            return {
                enabled: document.getElementById('livemap-enabled')?.checked ?? true,
                max_nodes: parseInt(document.getElementById('livemap-max-nodes')?.value, 10) || 1000,
                link_distance: parseInt(document.getElementById('livemap-link-distance')?.value, 10) || 60,
                charge_strength: parseInt(document.getElementById('livemap-charge-strength')?.value, 10) || -100,
                simplify: document.getElementById('livemap-default-simplify')?.checked ?? false,
                show_functions: document.getElementById('livemap-show-functions')?.checked ?? false,
            };
        },
        
        async load() {
            this.setStatus('Loading...', null);
            try {
                const resp = await this.request('/plugins/livemap/config');
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const config = await resp.json();
                
                const enabledEl = document.getElementById('livemap-enabled');
                const maxNodesEl = document.getElementById('livemap-max-nodes');
                const linkDistEl = document.getElementById('livemap-link-distance');
                const chargeEl = document.getElementById('livemap-charge-strength');
                const simplifyEl = document.getElementById('livemap-default-simplify');
                const showFuncEl = document.getElementById('livemap-show-functions');
                
                if (enabledEl) enabledEl.checked = config.enabled !== false;
                if (maxNodesEl) maxNodesEl.value = config.max_nodes ?? 1000;
                if (linkDistEl) linkDistEl.value = config.link_distance ?? 60;
                if (chargeEl) chargeEl.value = config.charge_strength ?? -100;
                if (simplifyEl) simplifyEl.checked = Boolean(config.simplify);
                if (showFuncEl) showFuncEl.checked = Boolean(config.show_functions);
                
                this.setStatus('');
            } catch (err) {
                console.error('[LiveMap Settings] Load failed:', err);
                this.setStatus('Error', 'error');
            }
        },
        
        async save() {
            const button = document.getElementById('livemap-save-btn');
            if (button) button.disabled = true;
            this.setStatus('Saving...', null);
            
            try {
                const resp = await this.request('/plugins/livemap/config', {
                    method: 'POST',
                    body: this.readPayload(),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                this.setStatus('Saved ✓', 'success');
                this.notify('Live Map settings saved', 'success');
            } catch (err) {
                console.error('[LiveMap Settings] Save failed:', err);
                this.setStatus('Error', 'error');
                this.notify('Failed to save settings', 'error');
            } finally {
                if (button) button.disabled = false;
            }
        },
        
        bind() {
            document.getElementById('livemap-save-btn')?.addEventListener('click', (e) => {
                e.preventDefault();
                this.save();
            });
        },
        
        init() {
            this.bind();
            this.load();
        }
    };
    
    window.livemapSettings = livemapSettings;
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => livemapSettings.init());
    } else {
        livemapSettings.init();
    }
})();
"""
