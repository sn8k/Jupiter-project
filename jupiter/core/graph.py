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

    def build(self) -> DependencyGraph:
        # Auto-simplify if too many files
        if not self.simplify and len(self.files) > self.max_nodes:
            self.simplify = True

        if self.simplify:
            self._build_simplified()
        else:
            self._build_detailed()
        
        return DependencyGraph(
            nodes=list(self.nodes.values()),
            links=self.links
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
            path = file["path"]
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
            source_path = file["path"]
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
        path = file["path"]
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
            if target_path:
                # In detailed mode, target is the file ID (path)
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
        # Very basic resolution: check if any file path ends with the import name converted to path
        # e.g. "jupiter.core.scanner" -> "jupiter/core/scanner.py"
        
        expected_suffix = import_name.replace(".", "/") + ".py"
        
        for file in self.files:
            if file["path"].endswith(expected_suffix):
                return file["path"]
        return None
