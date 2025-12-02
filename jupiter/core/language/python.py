# jupiter/core/language/python.py
# Version: 1.3.0
"""
Python source code analyzer for Jupiter.

Extracts imports, function definitions, function calls, and detects
potentially unused functions with improved heuristics to reduce false positives.

v1.2.0 Changes:
- Added detection of functions in dictionary values (CLI_HANDLERS, etc.)
- Added detection of getattr() calls
- Added test function exclusion (test_*, pytest fixtures)
- Added AST visitor method exclusion (visit_*)
- Added interface method detection
- Added __all__ export detection
- Improved callback detection patterns
"""

import ast
import re
from pathlib import Path
from typing import Dict, Any, Set, Optional, List


# =============================================================================
# FRAMEWORK DECORATORS - Functions with these decorators are considered "used"
# =============================================================================
FRAMEWORK_DECORATORS = frozenset({
    # FastAPI / Starlette
    "router.get", "router.post", "router.put", "router.delete", "router.patch",
    "router.options", "router.head", "router.trace", "router.websocket",
    "app.get", "app.post", "app.put", "app.delete", "app.patch",
    "app.on_event", "app.middleware", "app.exception_handler",
    "APIRouter", "Depends",
    # Flask
    "route", "get", "post", "put", "delete", "patch",
    "before_request", "after_request", "teardown_request",
    "errorhandler", "context_processor",
    # Click / Typer CLI
    "click.command", "click.group", "click.option", "click.argument",
    "command", "group", "callback",
    "app.command", "typer.command",
    # Tests
    "pytest.fixture", "fixture",
    "pytest.mark", "mark.parametrize", "mark.skip", "mark.skipif",
    "pytest.mark.asyncio", "asyncio",
    # Standard Python
    "abstractmethod", "staticmethod", "classmethod", "property",
    "cached_property", "lru_cache", "cache", "functools.lru_cache",
    "overload", "final",
    # Celery / Background tasks
    "task", "shared_task", "periodic_task",
    # Django
    "admin.register", "receiver", "login_required", "permission_required",
    # Dataclass / Pydantic
    "validator", "field_validator", "model_validator", "computed_field",
    "dataclass", "dataclasses.dataclass",
    # Event handlers
    "on_event", "event_handler", "listener",
})


# =============================================================================
# KNOWN USED PATTERNS - Methods that are implicitly used
# =============================================================================
KNOWN_USED_PATTERNS = frozenset({
    # Python dunder methods (always implicitly used)
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
    "__post_init__",  # Dataclass hook
    "__reduce__", "__reduce_ex__", "__getstate__", "__setstate__",  # Pickle
    # Serialization conventions
    "to_dict", "from_dict", "to_json", "from_json", "as_dict", "asdict",
    "serialize", "deserialize", "to_yaml", "from_yaml",
    "to_string", "from_string", "to_bytes", "from_bytes",
    "dict", "json", "copy", "deepcopy",
    # Pydantic / BaseModel
    "model_validate", "model_dump", "model_json_schema",
    "schema", "construct", "parse_obj", "parse_raw",
    # ORM / Database patterns
    "save", "delete", "refresh", "update", "create",
    "get_queryset", "get_object", "perform_create", "perform_update",
    # Plugin system hooks
    "on_scan", "on_analyze", "on_report", "on_startup", "on_shutdown",
    "setup", "teardown", "configure", "initialize", "cleanup",
    "hook_on_scan", "hook_on_analyze",  # Jupiter plugin hooks
    # Test patterns
    "setUp", "tearDown", "setUpClass", "tearDownClass",
    "setUpModule", "tearDownModule",
    # ABC / Interface patterns
    "get", "post", "put", "delete", "patch", "head", "options",
    "scan", "analyze", "run_command",  # Connector interface methods
    "get_api_base_url",  # Connector interface
    # Common callbacks
    "callback", "handler", "process", "execute", "run",
    # WebSocket
    "websocket_endpoint", "on_connect", "on_disconnect", "on_message",
    # Plugin UI methods (called via getattr)
    "get_ui_html", "get_ui_js", "get_settings_html", "get_settings_js",
    "get_state", "get_last_report", "update_from_report", "get_summary",
    "get_last_summary", "get_diagnostics_for_file",
    # Common utility names
    "main", "cli", "app",
    # Introspection functions
    "get_cli_handlers", "get_api_handlers", "get_handlers",
    # Plugin manager methods (called from API)
    "get_plugins_info", "get_sidebar_plugins", "get_settings_plugins",
    "get_plugin_ui_html", "get_plugin_ui_js", 
    "get_plugin_settings_html", "get_plugin_settings_js",
    "update_plugin_config", "enable_plugin", "restart_plugin",
    "install_plugin_from_url", "install_plugin_from_bytes", "uninstall_plugin",
    # Server manager methods
    "get_connector", "get_active_project", "get_default_connector",
    "create_project", "delete_project", "list_backends", "get_projects",
    # History methods
    "create_snapshot", "list_snapshots", "compare_snapshots", "get_snapshot",
    # Meeting adapter methods
    "heartbeat", "notify_online", "refresh_license", "validate_feature_access",
    "get_license_status", "last_seen_payload",
    # Cache methods
    "load_analysis_cache", "save_analysis_cache", "clear_cache",
    # State methods
    "load_last_root", "save_last_root", "load_default_project_root",
    # Watch methods
    "broadcast_file_change", "broadcast_log_message", "record_function_calls",
    "get_watch_state", "set_main_loop", "create_scan_progress_callback",
    # Quality methods
    "estimate_complexity", "estimate_js_complexity", "find_duplications",
    # Updater
    "apply_update",
    # Server API lifecycle
    "start", "stop", "ws_endpoint_route",
    # System services
    "history_manager", "load_effective_config", "save_effective_config",
    "preserve_meeting_config", "rebuild_runtime",
})


# =============================================================================
# DYNAMIC REGISTRATION METHODS - Track functions passed as arguments
# =============================================================================
DYNAMIC_REGISTRATION_METHODS = frozenset({
    "set_defaults",    # argparse: parser.set_defaults(func=handler)
    "add_command",     # CLI: app.add_command(cmd)
    "register",        # Generic registration
    "subscribe",       # Event subscription
    "connect",         # Signal connection (Django)
    "add_handler",     # Handler registration
    "on",              # Event: emitter.on("event", handler)
    "addEventListener", # JS-style
    "include_router",  # FastAPI router inclusion
    "add_api_route",   # FastAPI dynamic route
    "add_route",       # Generic route addition
    "settrace",        # sys.settrace(callback)
    "setprofile",      # sys.setprofile(callback)
})


# =============================================================================
# HANDLER DICT NAMES - Dictionaries that register handlers
# =============================================================================
HANDLER_DICT_NAMES = frozenset({
    "CLI_HANDLERS",
    "API_HANDLERS", 
    "HANDLERS",
    "COMMANDS",
    "ROUTES",
    "ENDPOINTS",
    "EVENT_HANDLERS",
    "CALLBACKS",
    "REGISTRY",
    "handlers",
    "commands",
    "routes",
})


# =============================================================================
# TEST FUNCTION PATTERNS - Regex patterns for test functions
# =============================================================================
TEST_FUNCTION_PATTERNS = [
    re.compile(r'^test_'),           # pytest: test_*
    re.compile(r'^Test'),            # unittest: TestCase classes
    re.compile(r'_test$'),           # *_test suffix
    re.compile(r'^check_'),          # check_* validation helpers in tests
]


# =============================================================================
# AST VISITOR PATTERNS - Patterns for AST visitor methods
# =============================================================================
AST_VISITOR_PATTERNS = [
    re.compile(r'^visit_'),          # ast.NodeVisitor.visit_*
    re.compile(r'^generic_visit'),   # ast.NodeVisitor.generic_visit
    re.compile(r'^depart_'),         # docutils visitor pattern
    re.compile(r'^leave_'),          # Alternative visitor pattern
]


class PythonCodeAnalyzer(ast.NodeVisitor):
    """
    AST visitor that extracts code structure information.
    
    Tracks:
    - Imports
    - Function definitions (with decorator analysis)
    - Function calls (including dynamic registrations)
    - Decorated functions (framework handlers)
    - Functions in handler dictionaries
    - Functions exported in __all__
    - Functions accessed via getattr
    """
    
    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or ""
        self.imports: Set[str] = set()
        self.function_calls: Set[str] = set()
        self.defined_functions: Set[str] = set()
        self.decorated_functions: Set[str] = set()  # Functions with framework decorators
        self.dynamically_registered: Set[str] = set()  # Functions passed to registration methods
        self.dict_registered: Set[str] = set()  # Functions in handler dicts
        self.exported_in_all: Set[str] = set()  # Functions in __all__
        self.getattr_accessed: Set[str] = set()  # Functions accessed via getattr
        self.is_test_file = self._is_test_file()

    def _is_test_file(self) -> bool:
        """Check if this file is a test file."""
        if not self.file_path:
            return False
        path = Path(self.file_path)
        # Check if in tests/ directory or file starts with test_
        return (
            "tests" in path.parts or
            "test" in path.parts or
            path.name.startswith("test_") or
            path.name.endswith("_test.py")
        )

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Store the MODULE path, not the full path with symbol
        # E.g., "from jupiter.config import load_config" -> store "jupiter.config"
        # This allows the graph builder to resolve module paths to file paths correctly
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined_functions.add(node.name)
        # Analyze decorators
        self._analyze_decorators(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.defined_functions.add(node.name)
        # Analyze decorators
        self._analyze_decorators(node)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """
        Detect:
        1. __all__ = ["func1", "func2"] - exported symbols
        2. CLI_HANDLERS = {"cmd": handler_func} - handler registrations
        3. HANDLERS = {name: func} - generic handler dicts
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Check for __all__
                if target.id == "__all__":
                    self._extract_all_exports(node.value)
                # Check for handler dictionaries
                elif target.id in HANDLER_DICT_NAMES:
                    self._extract_dict_handlers(node.value)
        self.generic_visit(node)

    def _extract_all_exports(self, value: ast.expr):
        """Extract function names from __all__ = [...]"""
        if isinstance(value, (ast.List, ast.Tuple)):
            for elt in value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    self.exported_in_all.add(elt.value)

    def _extract_dict_handlers(self, value: ast.expr):
        """Extract function references from handler dictionaries."""
        if isinstance(value, ast.Dict):
            for v in value.values:
                if isinstance(v, ast.Name):
                    self.dict_registered.add(v.id)
                    self.function_calls.add(v.id)

    def _analyze_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
        """Check if function has framework decorators that imply usage."""
        for decorator in node.decorator_list:
            dec_name = self._get_decorator_name(decorator)
            if dec_name and self._is_framework_decorator(dec_name):
                self.decorated_functions.add(node.name)
                break  # One framework decorator is enough

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Extract the name of a decorator (handles @dec, @dec(), @obj.dec, etc.)."""
        if isinstance(decorator, ast.Call):
            # @decorator(args) -> get the function being called
            return self._get_decorator_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            # @router.get or @app.route
            base = self._get_decorator_name(decorator.value)
            return f"{base}.{decorator.attr}" if base else decorator.attr
        elif isinstance(decorator, ast.Name):
            # @decorator
            return decorator.id
        return ""

    def _is_framework_decorator(self, dec_name: str) -> bool:
        """Check if decorator indicates the function is used by a framework."""
        if not dec_name:
            return False
        # Exact match
        if dec_name in FRAMEWORK_DECORATORS:
            return True
        # Partial match (e.g., "router.get" matches "my_router.get")
        for pattern in FRAMEWORK_DECORATORS:
            if dec_name.endswith(f".{pattern}") or dec_name.endswith(pattern.split(".")[-1]):
                # Be careful with simple names like "get" - require dot prefix
                if "." in pattern or dec_name == pattern:
                    return True
        return False

    def visit_Call(self, node: ast.Call):
        # Track direct function calls
        if isinstance(node.func, ast.Name):
            self.function_calls.add(node.func.id)
            # Check for getattr calls
            if node.func.id == "getattr":
                self._handle_getattr(node)
        elif isinstance(node.func, ast.Attribute):
            self.function_calls.add(node.func.attr)
            # Check for dynamic registration patterns
            self._check_dynamic_registration(node)
        
        # Track functions passed as arguments (callbacks, handlers)
        self._track_function_arguments(node)
        
        self.generic_visit(node)

    def _handle_getattr(self, node: ast.Call):
        """
        Handle getattr(obj, "method_name") calls.
        The method name is considered "used".
        """
        if len(node.args) >= 2:
            attr_arg = node.args[1]
            if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str):
                self.getattr_accessed.add(attr_arg.value)
                self.function_calls.add(attr_arg.value)

    def _check_dynamic_registration(self, node: ast.Call):
        """
        Detect dynamic function registration like:
        - parser.set_defaults(func=handler)
        - app.add_command(my_command)
        - emitter.on("event", handler)
        - sys.settrace(trace_func)
        """
        if not isinstance(node.func, ast.Attribute):
            return
        
        method_name = node.func.attr
        if method_name not in DYNAMIC_REGISTRATION_METHODS:
            return
        
        # Check keyword arguments (e.g., func=handler)
        for keyword in node.keywords:
            if keyword.arg in ("func", "handler", "callback", "command", "target"):
                if isinstance(keyword.value, ast.Name):
                    self.dynamically_registered.add(keyword.value.id)
                    self.function_calls.add(keyword.value.id)
        
        # Check positional arguments for function references
        for arg in node.args:
            if isinstance(arg, ast.Name):
                # Heuristic: if it's passed to a registration method, it's likely a handler
                self.dynamically_registered.add(arg.id)
                self.function_calls.add(arg.id)

    def _track_function_arguments(self, node: ast.Call):
        """
        Track function names passed as arguments to other functions.
        This catches patterns like: map(func, items), filter(predicate, items), etc.
        """
        for arg in node.args:
            if isinstance(arg, ast.Name):
                # Could be a function reference
                self.function_calls.add(arg.id)
        
        for keyword in node.keywords:
            if isinstance(keyword.value, ast.Name):
                # Could be a function reference
                self.function_calls.add(keyword.value.id)


def is_likely_used(func_name: str, file_path: Optional[str] = None) -> bool:
    """
    Check if a function name matches patterns that indicate implicit usage.
    
    Returns True for:
    - Dunder methods (__init__, __str__, etc.)
    - Known serialization methods (to_dict, from_json, etc.)
    - Plugin hooks (on_scan, setup, etc.)
    - Test functions in test files
    - AST visitor methods (visit_*)
    - Handler-style names (handle_*, on_*)
    """
    # All dunder methods are implicitly used
    if func_name.startswith("__") and func_name.endswith("__"):
        return True
    
    # Check against known patterns
    if func_name in KNOWN_USED_PATTERNS:
        return True
    
    # Check if it's a test function pattern
    for pattern in TEST_FUNCTION_PATTERNS:
        if pattern.match(func_name):
            return True
    
    # Check if it's an AST visitor method
    for pattern in AST_VISITOR_PATTERNS:
        if pattern.match(func_name):
            return True
    
    # Handler patterns: handle_*, on_*, hook_*
    if func_name.startswith(("handle_", "on_", "hook_", "_handle_", "_on_")):
        return True
    
    # Callback patterns: *_callback, *_handler
    if func_name.endswith(("_callback", "_handler", "_hook")):
        return True
    
    # Private run methods often called internally
    if func_name.startswith("_run_") or func_name.startswith("_process_"):
        return True
    
    return False


def is_test_function(func_name: str, file_path: Optional[str] = None) -> bool:
    """Check if a function is a test function."""
    # Check name patterns
    for pattern in TEST_FUNCTION_PATTERNS:
        if pattern.match(func_name):
            return True
    
    # Check file path if provided
    if file_path:
        path = Path(file_path)
        if "tests" in path.parts or "test" in path.parts:
            return True
        if path.name.startswith("test_") or path.name.endswith("_test.py"):
            return True
    
    return False


def analyze_python_source(source_code: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyzes Python source code to extract imports, function definitions, and calls.
    
    Uses improved heuristics to reduce false positives in unused function detection:
    - Recognizes framework decorators (FastAPI, Click, pytest, etc.)
    - Whitelist for dunder methods and common patterns
    - Tracks dynamic function registrations (argparse, event handlers)
    - Detects functions in handler dictionaries (CLI_HANDLERS, etc.)
    - Recognizes getattr() calls
    - Excludes test functions in test files
    - Excludes AST visitor methods (visit_*)
    
    Args:
        source_code: Python source code to analyze
        file_path: Optional path to the source file (used for test file detection)
    
    Returns:
        Dict with keys:
        - imports: List of imported module names
        - defined_functions: List of all function names defined
        - function_calls: List of function names that are called
        - potentially_unused_functions: List of functions that appear unused
        - decorated_functions: List of functions with framework decorators
        - dynamically_registered: List of functions registered dynamically
        - dict_registered: List of functions in handler dictionaries
        - exported_in_all: List of functions in __all__
        - getattr_accessed: List of functions accessed via getattr
    """
    try:
        tree = ast.parse(source_code)
        analyzer = PythonCodeAnalyzer(file_path)
        analyzer.visit(tree)

        # Compute potentially unused functions with improved heuristics
        potentially_unused = set()
        for func_name in analyzer.defined_functions:
            # Skip if directly called
            if func_name in analyzer.function_calls:
                continue
            # Skip if has framework decorator
            if func_name in analyzer.decorated_functions:
                continue
            # Skip if dynamically registered
            if func_name in analyzer.dynamically_registered:
                continue
            # Skip if registered in a handler dict
            if func_name in analyzer.dict_registered:
                continue
            # Skip if exported in __all__
            if func_name in analyzer.exported_in_all:
                continue
            # Skip if accessed via getattr
            if func_name in analyzer.getattr_accessed:
                continue
            # Skip if matches known used patterns (dunder, serialization, etc.)
            if is_likely_used(func_name, file_path):
                continue
            # Skip test functions in test files
            if analyzer.is_test_file and is_test_function(func_name, file_path):
                continue
            # This function is potentially unused
            potentially_unused.add(func_name)

        return {
            "imports": sorted(list(analyzer.imports)),
            "defined_functions": sorted(list(analyzer.defined_functions)),
            "function_calls": sorted(list(analyzer.function_calls)),
            "potentially_unused_functions": sorted(list(potentially_unused)),
            "decorated_functions": sorted(list(analyzer.decorated_functions)),
            "dynamically_registered": sorted(list(analyzer.dynamically_registered)),
            "dict_registered": sorted(list(analyzer.dict_registered)),
            "exported_in_all": sorted(list(analyzer.exported_in_all)),
            "getattr_accessed": sorted(list(analyzer.getattr_accessed)),
            "is_test_file": analyzer.is_test_file,
        }
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}
