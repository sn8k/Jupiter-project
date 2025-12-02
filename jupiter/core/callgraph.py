# jupiter/core/callgraph.py
# Version: 1.0.0
"""
Global call graph builder for Jupiter.

This module builds a complete call graph across the entire project by:
1. Collecting ALL function definitions from ALL files
2. Collecting ALL function calls/references from ALL files
3. Resolving which functions are actually used (directly or indirectly)

Unlike per-file analysis, this approach can detect:
- Cross-file calls
- Functions passed as callbacks
- Functions registered in dictionaries
- Entry points (main, CLI handlers, API endpoints)

The goal is TRUE detection, not pattern-based heuristics.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# MINIMAL IMPLICIT PATTERNS - Only truly implicit usage (no workarounds!)
# =============================================================================

# Dunder methods are ALWAYS implicitly used by Python runtime
DUNDER_METHODS = frozenset({
    "__init__", "__new__", "__del__", "__repr__", "__str__", "__bytes__",
    "__format__", "__hash__", "__bool__", "__sizeof__",
    "__call__", "__len__", "__length_hint__", "__getitem__", "__setitem__",
    "__delitem__", "__missing__", "__iter__", "__next__", "__reversed__",
    "__contains__", "__add__", "__sub__", "__mul__", "__truediv__",
    "__floordiv__", "__mod__", "__pow__", "__lshift__", "__rshift__",
    "__and__", "__or__", "__xor__", "__neg__", "__pos__", "__abs__",
    "__invert__", "__complex__", "__int__", "__float__", "__index__",
    "__round__", "__trunc__", "__floor__", "__ceil__", "__enter__", "__exit__",
    "__await__", "__aiter__", "__anext__", "__aenter__", "__aexit__",
    "__get__", "__set__", "__delete__", "__set_name__",
    "__init_subclass__", "__class_getitem__", "__prepare__",
    "__getattr__", "__setattr__", "__delattr__", "__getattribute__",
    "__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__",
    "__post_init__",
    "__reduce__", "__reduce_ex__", "__getstate__", "__setstate__",
})

# Visitor pattern methods - called dynamically by visitor frameworks
# These are TRULY implicit because the base class uses getattr("visit_" + node_type)
VISITOR_PATTERN_PREFIXES = (
    "visit_",       # ast.NodeVisitor, docutils, etc.
    "depart_",      # docutils
    "leave_",       # Alternative visitor pattern
    "generic_visit", # ast.NodeVisitor fallback
)

# Framework decorators that mark entry points
ENTRY_POINT_DECORATORS = frozenset({
    # FastAPI / Starlette
    "router.get", "router.post", "router.put", "router.delete", "router.patch",
    "router.websocket", "app.get", "app.post", "app.put", "app.delete",
    "app.on_event", "app.middleware", "app.exception_handler",
    # Flask
    "route", "before_request", "after_request", "errorhandler",
    # Click / Typer CLI
    "click.command", "click.group", "command", "group", "callback",
    "app.command", "typer.command",
    # Tests
    "pytest.fixture", "fixture", "pytest.mark",
    # Celery
    "task", "shared_task", "periodic_task",
    # Django
    "admin.register", "receiver", "login_required",
    # ABC
    "abstractmethod",
})


@dataclass
class FunctionInfo:
    """Complete information about a function definition."""
    name: str
    file_path: str
    line_number: int
    is_method: bool = False
    class_name: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_entry_point: bool = False  # Marked by framework decorator
    is_dunder: bool = False
    is_test: bool = False
    is_visitor_method: bool = False  # visit_*, depart_*, etc.
    is_abstract: bool = False  # Has @abstractmethod
    is_interface_impl: bool = False  # Implements an abstract method
    
    @property
    def full_name(self) -> str:
        """Return fully qualified name: file::class.method or file::function"""
        if self.class_name:
            return f"{self.file_path}::{self.class_name}.{self.name}"
        return f"{self.file_path}::{self.name}"
    
    @property
    def simple_key(self) -> str:
        """Return simple key: file::func (without class name)"""
        return f"{self.file_path}::{self.name}"
    
    @property
    def short_key(self) -> str:
        """Return short key for matching: class.method or function.
        
        Used for matching function references without file path context.
        Useful for cross-file call detection and debugging output.
        Note: May appear unused in static analysis but is part of the dataclass API.
        """
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name
    
    @property
    def is_implicitly_used(self) -> bool:
        """Check if function is implicitly used (dunder, visitor, etc.).
        
        Returns True for functions that are called by Python runtime or frameworks:
        - Dunder methods (__init__, __str__, etc.)
        - Visitor pattern methods (visit_*, depart_*)
        - Test functions (test_*)
        - Decorated entry points (@router.get, @fixture)
        - Interface implementations
        
        Note: May appear unused in static analysis but is part of the dataclass API.
        """
        return (
            self.is_dunder or 
            self.is_visitor_method or 
            self.is_test or 
            self.is_entry_point or
            self.is_interface_impl
        )


@dataclass
class CallReference:
    """A reference to a function (call, assignment, etc.)"""
    name: str  # Function name being called/referenced
    file_path: str
    line_number: int
    context: str  # "call", "reference", "dict_value", "callback", "getattr"
    target_attr: Optional[str] = None  # For method calls: obj.method -> method
    

@dataclass
class CallGraphResult:
    """Result of call graph analysis."""
    # All defined functions
    all_functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    # All references (calls, assignments, etc.)
    all_references: List[CallReference] = field(default_factory=list)
    # Functions that are definitely used (reachable from entry points)
    used_functions: Set[str] = field(default_factory=set)
    # Functions that appear unused
    unused_functions: Set[str] = field(default_factory=set)
    # Entry points (main, decorated handlers, etc.)
    entry_points: Set[str] = field(default_factory=set)
    # Debug: why each function is considered used
    usage_reasons: Dict[str, List[str]] = field(default_factory=dict)


class CallGraphVisitor(ast.NodeVisitor):
    """
    AST visitor that extracts function definitions and ALL references.
    
    This visitor is more thorough than per-file analysis:
    - Tracks function references in ANY context (not just calls)
    - Tracks method calls and attribute access
    - Tracks dictionary values
    - Tracks getattr/hasattr access
    """
    
    def __init__(self, file_path: str, root: Path):
        self.file_path = file_path
        self.root = root
        self.rel_path = self._get_rel_path()
        
        # Current context
        self.current_class: Optional[str] = None
        
        # Collected data
        self.functions: List[FunctionInfo] = []
        self.references: List[CallReference] = []
        self.exported_names: Set[str] = set()  # From __all__
    
    def _get_rel_path(self) -> str:
        """Get relative path for consistent keys."""
        try:
            return Path(self.file_path).relative_to(self.root).as_posix()
        except ValueError:
            return self.file_path
    
    def _is_test_file(self) -> bool:
        """Check if this is a test file."""
        path = Path(self.file_path)
        return (
            "tests" in path.parts or
            "test" in path.parts or
            path.name.startswith("test_") or
            path.name.endswith("_test.py")
        )
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract full decorator name."""
        if isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            base = self._get_decorator_name(decorator.value)
            return f"{base}.{decorator.attr}" if base else decorator.attr
        elif isinstance(decorator, ast.Name):
            return decorator.id
        return ""
    
    def _is_entry_point_decorator(self, dec_name: str) -> bool:
        """Check if decorator marks an entry point."""
        if dec_name in ENTRY_POINT_DECORATORS:
            return True
        # Partial match for patterns like "my_router.get"
        for pattern in ENTRY_POINT_DECORATORS:
            if "." in pattern and dec_name.endswith(pattern):
                return True
            parts = pattern.split(".")
            if len(parts) == 2 and dec_name.endswith(f".{parts[1]}"):
                return True
        return False
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class context for methods."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._process_function(node)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._process_function(node)
        self.generic_visit(node)
    
    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Process a function definition."""
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        is_entry = any(self._is_entry_point_decorator(d) for d in decorators)
        is_test = self._is_test_file() and (
            node.name.startswith("test_") or 
            node.name.startswith("Test")
        )
        is_visitor = any(node.name.startswith(prefix) for prefix in VISITOR_PATTERN_PREFIXES)
        is_abstract = "abstractmethod" in decorators
        
        func_info = FunctionInfo(
            name=node.name,
            file_path=self.rel_path,
            line_number=node.lineno,
            is_method=self.current_class is not None,
            class_name=self.current_class,
            decorators=decorators,
            is_entry_point=is_entry,
            is_dunder=node.name.startswith("__") and node.name.endswith("__"),
            is_test=is_test,
            is_visitor_method=is_visitor,
            is_abstract=is_abstract,
        )
        self.functions.append(func_info)
    
    def visit_Call(self, node: ast.Call):
        """Track function calls."""
        if isinstance(node.func, ast.Name):
            # Direct call: func()
            self.references.append(CallReference(
                name=node.func.id,
                file_path=self.rel_path,
                line_number=node.lineno,
                context="call",
            ))
            # Special handling for getattr/hasattr
            if node.func.id in ("getattr", "hasattr") and len(node.args) >= 2:
                self._handle_attr_lookup(node)
        elif isinstance(node.func, ast.Attribute):
            # Method call: obj.method()
            self.references.append(CallReference(
                name=node.func.attr,
                file_path=self.rel_path,
                line_number=node.lineno,
                context="call",
                target_attr=node.func.attr,
            ))
        self.generic_visit(node)
    
    def _handle_attr_lookup(self, node: ast.Call):
        """Handle getattr(obj, "attr") / hasattr(obj, "attr")."""
        if len(node.args) >= 2:
            attr_arg = node.args[1]
            if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str):
                self.references.append(CallReference(
                    name=attr_arg.value,
                    file_path=self.rel_path,
                    line_number=node.lineno,
                    context="getattr",
                ))
    
    def visit_Attribute(self, node: ast.Attribute):
        """Track attribute access (even without call)."""
        # This catches obj.method without ()
        self.references.append(CallReference(
            name=node.attr,
            file_path=self.rel_path,
            line_number=node.lineno,
            context="reference",
            target_attr=node.attr,
        ))
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """Track name references (function passed as value)."""
        # Only in Load context (reading the name)
        if isinstance(node.ctx, ast.Load):
            self.references.append(CallReference(
                name=node.id,
                file_path=self.rel_path,
                line_number=node.lineno,
                context="reference",
            ))
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """Track __all__ exports and dict registrations."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id == "__all__":
                    self._extract_all_exports(node.value)
        # Continue to visit the value side for dict handlers, etc.
        self.generic_visit(node)
    
    def _extract_all_exports(self, value: ast.expr):
        """Extract names from __all__ = [...]"""
        if isinstance(value, (ast.List, ast.Tuple)):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.exported_names.add(elt.value)


class CallGraphBuilder:
    """
    Builds a complete call graph for a project.
    
    Usage:
        builder = CallGraphBuilder(project_root)
        result = builder.build(python_files)
        
        for func_key in result.unused_functions:
            info = result.all_functions[func_key]
            print(f"Unused: {info.full_name} at line {info.line_number}")
    """
    
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
    
    def build(self, python_files: List[Path]) -> CallGraphResult:
        """
        Build call graph from Python files.
        
        Args:
            python_files: List of Python file paths to analyze
            
        Returns:
            CallGraphResult with all functions and usage information
        """
        result = CallGraphResult()
        
        # Phase 1: Collect all definitions and references
        for file_path in python_files:
            try:
                self._analyze_file(file_path, result)
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")
        
        # Phase 2: Identify interface implementations
        self._identify_interface_implementations(result)
        
        # Phase 3: Identify entry points
        self._identify_entry_points(result)
        
        # Phase 4: Propagate usage from entry points
        self._propagate_usage(result)
        
        # Phase 5: Identify unused functions
        self._identify_unused(result)
        
        return result
    
    def _identify_interface_implementations(self, result: CallGraphResult):
        """
        Identify methods that implement abstract interfaces.
        
        If a method has the same name as an abstract method somewhere in the project,
        it's likely an implementation and should be considered used.
        """
        # Collect all abstract method names
        abstract_method_names: Set[str] = set()
        for func in result.all_functions.values():
            if func.is_abstract and func.is_method:
                abstract_method_names.add(func.name)
        
        # Mark implementations
        for key, func in result.all_functions.items():
            if func.is_method and func.name in abstract_method_names and not func.is_abstract:
                func.is_interface_impl = True
    
    def _analyze_file(self, file_path: Path, result: CallGraphResult):
        """Analyze a single file and add to result."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            logger.debug(f"Syntax error in {file_path}: {e}")
            return
        
        visitor = CallGraphVisitor(str(file_path), self.root)
        visitor.visit(tree)
        
        # Add functions to global registry
        for func in visitor.functions:
            result.all_functions[func.full_name] = func
        
        # Add references
        result.all_references.extend(visitor.references)
    
    def _identify_entry_points(self, result: CallGraphResult):
        """
        Identify all entry points in the project.
        
        Entry points are:
        - Functions with framework decorators (@router.get, @fixture, etc.)
        - Functions named 'main'
        - Dunder methods (implicitly called by Python)
        - Test functions (called by pytest)
        - Functions exported in __all__
        """
        for key, func in result.all_functions.items():
            reasons = []
            
            # Framework-decorated functions
            if func.is_entry_point:
                reasons.append(f"has_decorator:{func.decorators}")
            
            # Dunder methods
            if func.is_dunder:
                reasons.append("dunder_method")
            
            # Test functions
            if func.is_test:
                reasons.append("test_function")
            
            # Visitor pattern methods
            if func.is_visitor_method:
                reasons.append("visitor_method")
            
            # Interface implementations
            if func.is_interface_impl:
                reasons.append("interface_implementation")
            
            # Main function
            if func.name == "main":
                reasons.append("main_entry_point")
            
            # If any reason, mark as entry point
            if reasons:
                result.entry_points.add(key)
                result.used_functions.add(key)
                result.usage_reasons[key] = reasons
    
    def _propagate_usage(self, result: CallGraphResult):
        """
        Propagate usage from entry points through the call graph.
        
        A function is "used" if:
        1. It's an entry point, OR
        2. It's referenced by name anywhere in the project
        
        NOTE: This is a simplified version that marks any referenced name as used.
        A more precise version would track call chains, but this avoids false positives.
        """
        # Build a name -> keys index
        name_to_keys: Dict[str, List[str]] = {}
        for key, func in result.all_functions.items():
            if func.name not in name_to_keys:
                name_to_keys[func.name] = []
            name_to_keys[func.name].append(key)
        
        # Collect all referenced names
        referenced_names: Set[str] = set()
        for ref in result.all_references:
            referenced_names.add(ref.name)
            if ref.target_attr:
                referenced_names.add(ref.target_attr)
        
        # Mark functions as used if their name is referenced
        for name in referenced_names:
            for key in name_to_keys.get(name, []):
                if key not in result.used_functions:
                    result.used_functions.add(key)
                    if key not in result.usage_reasons:
                        result.usage_reasons[key] = []
                    result.usage_reasons[key].append(f"name_referenced:{name}")
    
    def _identify_unused(self, result: CallGraphResult):
        """Identify functions that are not used."""
        for key in result.all_functions:
            if key not in result.used_functions:
                result.unused_functions.add(key)


def build_call_graph(root: Path, python_files: List[Path]) -> CallGraphResult:
    """
    Convenience function to build a call graph.
    
    Args:
        root: Project root path
        python_files: List of Python files to analyze
        
    Returns:
        CallGraphResult with usage information
    """
    builder = CallGraphBuilder(root)
    return builder.build(python_files)


# =============================================================================
# CALL GRAPH SERVICE - High-level API for Jupiter components
# =============================================================================

class CallGraphService:
    """
    High-level service for call graph analysis.
    
    This service provides a convenient API for other Jupiter components
    to access call graph functionality:
    - Plugins (code_quality, autodiag, etc.)
    - Server API endpoints
    - CLI commands
    
    Usage:
        service = CallGraphService(project_root)
        
        # Get all unused functions
        unused = service.get_unused_functions()
        
        # Check if a specific function is used
        is_used = service.is_function_used("jupiter/core/scanner.py", "iter_files")
        
        # Get usage reasons for a function
        reasons = service.get_usage_reasons("jupiter/core/scanner.py", "iter_files")
        
        # Get full analysis result
        result = service.analyze()
    """
    
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self._result: Optional[CallGraphResult] = None
        self._last_analysis_time: float = 0
    
    def analyze(self, force: bool = False) -> CallGraphResult:
        """
        Run call graph analysis on the project.
        
        Args:
            force: Force re-analysis even if cached result exists
            
        Returns:
            CallGraphResult with complete analysis
        """
        if self._result is not None and not force:
            return self._result
        
        # Collect Python files
        python_files = list(self.root.glob("**/*.py"))
        # Exclude common non-project directories
        python_files = [
            f for f in python_files
            if not any(part.startswith(".") for part in f.parts)
            and "__pycache__" not in f.parts
            and "node_modules" not in f.parts
            and ".venv" not in f.parts
            and "venv" not in f.parts
        ]
        
        import time
        start = time.time()
        self._result = build_call_graph(self.root, python_files)
        self._last_analysis_time = time.time() - start
        
        logger.info(
            "Call graph analysis completed in %.2fs: %d functions, %d unused",
            self._last_analysis_time,
            len(self._result.all_functions),
            len(self._result.unused_functions),
        )
        
        return self._result
    
    def get_unused_functions(self) -> List[Dict[str, Any]]:
        """
        Get list of unused functions with details.
        
        Returns:
            List of dicts with function info (name, file, line, reasons)
        """
        result = self.analyze()
        
        unused_list = []
        for key in sorted(result.unused_functions):
            func = result.all_functions.get(key)
            if func:
                unused_list.append({
                    "name": func.name,
                    "file_path": func.file_path,
                    "line_number": func.line_number,
                    "class_name": func.class_name,
                    "full_name": func.full_name,
                    "simple_key": func.simple_key,
                    "is_method": func.is_method,
                })
        
        return unused_list
    
    def is_function_used(self, file_path: str, func_name: str) -> bool:
        """
        Check if a function is used.
        
        Args:
            file_path: Relative path to the file
            func_name: Function name
            
        Returns:
            True if function is used, False otherwise
        """
        result = self.analyze()
        key = f"{file_path}::{func_name}"
        
        # Check both simple key and full name
        for func_key in result.used_functions:
            func = result.all_functions.get(func_key)
            if func and (func.simple_key == key or func_key == key):
                return True
        
        return False
    
    def get_usage_reasons(self, file_path: str, func_name: str) -> List[str]:
        """
        Get reasons why a function is considered used.
        
        Args:
            file_path: Relative path to the file
            func_name: Function name
            
        Returns:
            List of reasons (empty if function is unused)
        """
        result = self.analyze()
        
        # Find the function
        for key, func in result.all_functions.items():
            if func.simple_key == f"{file_path}::{func_name}":
                return result.usage_reasons.get(key, [])
        
        return []
    
    def get_entry_points(self) -> List[Dict[str, Any]]:
        """
        Get list of entry points (decorated handlers, main, tests, etc.)
        
        Returns:
            List of entry point functions with their reasons
        """
        result = self.analyze()
        
        entry_points = []
        for key in sorted(result.entry_points):
            func = result.all_functions.get(key)
            if func:
                entry_points.append({
                    "name": func.name,
                    "file_path": func.file_path,
                    "line_number": func.line_number,
                    "reasons": result.usage_reasons.get(key, []),
                    "decorators": func.decorators,
                })
        
        return entry_points
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get call graph statistics.
        
        Returns:
            Dict with analysis statistics
        """
        result = self.analyze()
        
        return {
            "total_functions": len(result.all_functions),
            "entry_points": len(result.entry_points),
            "used_functions": len(result.used_functions),
            "unused_functions": len(result.unused_functions),
            "usage_rate": (
                len(result.used_functions) / len(result.all_functions) * 100
                if result.all_functions else 0
            ),
            "analysis_time_seconds": self._last_analysis_time,
        }
    
    def invalidate_cache(self):
        """Invalidate cached analysis result."""
        self._result = None
        self._last_analysis_time = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export full analysis as dictionary (for API/JSON).
        
        Returns:
            Complete analysis data as dict
        """
        result = self.analyze()
        
        return {
            "statistics": self.get_statistics(),
            "unused_functions": self.get_unused_functions(),
            "entry_points": self.get_entry_points(),
        }
