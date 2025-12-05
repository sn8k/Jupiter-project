"""
Live Map Plugin - Graph Builder
===============================

Builds dependency graphs from scan results.

Version: 0.3.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
    nodes: list[GraphNode] = field(default_factory=list)
    links: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dictionary."""
        return {
            "nodes": [asdict(n) for n in self.nodes],
            "links": [asdict(e) for e in self.links]
        }


class GraphBuilder:
    """Builds a dependency graph from scan results."""

    def __init__(self, files: list[dict[str, Any]], 
                 simplify: bool = False, 
                 max_nodes: int = 1000):
        """
        Initialize the graph builder.
        
        Args:
            files: List of file dictionaries from scan
            simplify: Whether to use simplified (directory-level) mode
            max_nodes: Maximum nodes before auto-enabling simplify
        """
        self.files = files
        self.simplify = simplify
        self.max_nodes = max_nodes
        self.nodes: dict[str, GraphNode] = {}
        self.links: list[GraphEdge] = []
        
        logger.debug(
            "GraphBuilder initialized: %d files, simplify=%s, max_nodes=%d",
            len(files), simplify, max_nodes
        )
        
        # Build lookup maps for faster import resolution
        self.file_map: dict[str, str] = {}
        self.filename_index: dict[str, list[str]] = {}
        
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
        logger.info("Building dependency graph (simplify=%s, files=%d)", 
                    self.simplify, len(self.files))
        
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
        
        if imports_found > 0:
            resolution_rate = int(imports_resolved / imports_found * 100)
        else:
            resolution_rate = 0
            
        logger.debug(
            "Detailed build complete: %d files processed, %d imports found, "
            "%d resolved (%d%% resolution rate)",
            processed, imports_found, imports_resolved, resolution_rate
        )

    def _build_simplified(self) -> None:
        """Build simplified graph grouped by directory."""
        logger.debug("Building simplified graph (directory-level nodes)")
        
        dir_sizes: dict[str, int] = {}
        file_to_dir: dict[str, str] = {}
        
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
        edges: set[tuple[str, str]] = set()
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

    def _process_file(self, file: dict[str, Any]) -> dict[str, int]:
        """Process a single file and add nodes/edges."""
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
        
        return {"imports_found": imports_found, "imports_resolved": imports_resolved}

    def _resolve_import_path(self, import_name: str) -> Optional[str]:
        """
        Resolve import name to file path.
        
        Handles Python imports (jupiter.core.scanner -> jupiter/core/scanner.py)
        and JS/TS relative imports.
        """
        if not import_name:
            return None
            
        # Skip external/stdlib packages
        if "." not in import_name and "/" not in import_name and "\\" not in import_name:
            for ext in (".py", ".js", ".ts", ".jsx", ".tsx"):
                if import_name + ext in self.file_map:
                    return self.file_map[import_name + ext]
            return None
        
        # Normalize path separators
        normalized = import_name.replace("\\", "/").replace(".", "/")
        
        if normalized.startswith("/"):
            normalized = normalized[1:]
        
        # Try multiple resolution strategies
        py_extensions = [".py", "/__init__.py"]
        js_extensions = [".js", ".ts", ".jsx", ".tsx", "/index.js", "/index.ts"]
        
        for ext in py_extensions + js_extensions:
            path_candidate = normalized + ext
            
            # Direct match
            if path_candidate in self.file_map:
                return self.file_map[path_candidate]
            
            # Suffix match
            for full_path in self.file_map:
                if full_path.endswith(path_candidate) or full_path.endswith("/" + path_candidate):
                    return full_path
        
        # Try progressively shorter paths
        parts = normalized.split("/")
        while len(parts) > 1:
            partial_path = "/".join(parts)
            for ext in py_extensions + js_extensions:
                path_candidate = partial_path + ext
                
                if path_candidate in self.file_map:
                    return self.file_map[path_candidate]
                
                for full_path in self.file_map:
                    if full_path.endswith(path_candidate) or full_path.endswith("/" + path_candidate):
                        return full_path
            
            parts = parts[:-1]
        
        # Fuzzy match on filename
        target_name = normalized.split("/")[-1] if "/" in normalized else normalized
        for ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
            candidates = self.filename_index.get(target_name + ext, [])
            
            parts = normalized.split("/")
            best_match = None
            best_score = 0
            
            for path in candidates:
                path_lower = path.lower()
                score = sum(1 for part in parts if part and part.lower() in path_lower and part != "..")
                if score > best_score:
                    best_score = score
                    best_match = path
            
            if best_match and best_score >= len(parts) * 0.5:
                return best_match
        
        return None
