"""Dependency graph generation for the Live Map."""

from typing import Any, Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class GraphNode:
    id: str
    type: str  # "file", "module", "function"
    label: str
    size: int = 0
    complexity: int = 0
    group: Optional[str] = None

@dataclass
class GraphEdge:
    source: str
    target: str
    type: str  # "import", "call"
    weight: int = 1

@dataclass
class DependencyGraph:
    nodes: List[GraphNode]
    links: List[GraphEdge]

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
        
        # Optimization: Build a lookup map for faster import resolution
        # Map: "path/to/file.py" -> "full/path/to/file.py"
        # We normalize to forward slashes and remove extensions for fuzzy matching if needed
        self.file_map: Dict[str, str] = {}
        self.filename_index: Dict[str, List[str]] = {} # filename -> list of full paths
        
        for f in self.files:
            path = f["path"].replace("\\", "/")
            self.file_map[path] = path
            
            filename = path.split("/")[-1]
            if filename not in self.filename_index:
                self.filename_index[filename] = []
            self.filename_index[filename].append(path)

    def build(self) -> DependencyGraph:
        # Auto-simplify if too many files
        if not self.simplify and len(self.files) > self.max_nodes:
            self.simplify = True

        if self.simplify:
            self._build_simplified()
        else:
            self._build_detailed()
        
        # Filter links to only include those where both source and target exist in nodes
        # This prevents D3.js "node not found" errors
        valid_links = [
            link for link in self.links
            if link.source in self.nodes and link.target in self.nodes
        ]
        
        return DependencyGraph(
            nodes=list(self.nodes.values()),
            links=valid_links
        )

    def _build_detailed(self):
        for file in self.files:
            self._process_file(file)

    def _build_simplified(self):
        # Group by directory
        dir_sizes = {}
        
        # Map file path to directory
        file_to_dir = {}
        
        for file in self.files:
            # Normalize path to use forward slashes consistently
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

        # Create edges
        edges = set() # (source_dir, target_dir)

        for file in self.files:
            # Normalize path to use forward slashes consistently
            source_path = file["path"].replace("\\", "/")
            source_dir = file_to_dir[source_path]
            
            lang_analysis = file.get("language_analysis") or {}
            imports = lang_analysis.get("imports", [])
            
            for imp in imports:
                target_path = self._resolve_import_path(imp)
                if target_path and target_path in file_to_dir:
                    target_dir = file_to_dir[target_path]
                    if source_dir != target_dir:
                        edges.add((source_dir, target_dir))

        for src, tgt in edges:
            self.links.append(GraphEdge(
                source=src,
                target=tgt,
                type="dependency"
            ))

    def _process_file(self, file: Dict[str, Any]):
        # Normalize path to use forward slashes consistently
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
        for imp in imports:
            # Heuristic: try to find if import matches another file in the project
            target_path = self._resolve_import_path(imp)
            if target_path and target_path in self.file_map:
                # In detailed mode, target is the file ID (path)
                # We store the link with resolved target; validation happens in build()
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

    def _resolve_import_path(self, import_name: str) -> Optional[str]:
        # Optimized resolution using lookup map
        # e.g. "jupiter.core.scanner" -> "jupiter/core/scanner.py"
        
        path_suffix = import_name.replace(".", "/") + ".py"
        
        # 1. Exact match (relative to root)
        if path_suffix in self.file_map:
            return self.file_map[path_suffix]

        # 2. Suffix match using filename index
        # Extract the filename from the import suffix
        target_filename = path_suffix.split("/")[-1]
        
        candidates = self.filename_index.get(target_filename, [])
        for path in candidates:
            if path.endswith(path_suffix):
                return path
                
        return None
