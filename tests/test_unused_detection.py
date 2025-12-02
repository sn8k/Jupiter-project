"""Tests for improved unused function detection in Python analyzer.

Version: 1.0.0

These tests validate the improved heuristics for reducing false positives
in the unused function detection feature.
"""

import pytest
from jupiter.core.language.python import (
    analyze_python_source,
    is_likely_used,
    FRAMEWORK_DECORATORS,
    KNOWN_USED_PATTERNS,
    DYNAMIC_REGISTRATION_METHODS,
    PythonCodeAnalyzer,
)


class TestFrameworkDecoratorDetection:
    """Test detection of framework decorators."""

    def test_fastapi_router_get(self):
        """FastAPI @router.get should not be marked unused."""
        code = '''
@router.get("/health")
def get_health():
    return {"status": "ok"}
'''
        result = analyze_python_source(code)
        assert "get_health" in result["decorated_functions"]
        assert "get_health" not in result["potentially_unused_functions"]

    def test_fastapi_router_post(self):
        """FastAPI @router.post should not be marked unused."""
        code = '''
@router.post("/scan")
async def run_scan():
    pass
'''
        result = analyze_python_source(code)
        assert "run_scan" in result["decorated_functions"]
        assert "run_scan" not in result["potentially_unused_functions"]

    def test_flask_route(self):
        """Flask @app.route should not be marked unused."""
        code = '''
@app.route("/hello")
def hello_world():
    return "Hello"
'''
        result = analyze_python_source(code)
        assert "hello_world" in result["decorated_functions"]
        assert "hello_world" not in result["potentially_unused_functions"]

    def test_click_command(self):
        """Click @click.command should not be marked unused."""
        code = '''
@click.command()
def my_command():
    print("Hello")
'''
        result = analyze_python_source(code)
        assert "my_command" in result["decorated_functions"]
        assert "my_command" not in result["potentially_unused_functions"]

    def test_pytest_fixture(self):
        """pytest @pytest.fixture should not be marked unused."""
        code = '''
@pytest.fixture
def sample_data():
    return {"key": "value"}
'''
        result = analyze_python_source(code)
        assert "sample_data" in result["decorated_functions"]
        assert "sample_data" not in result["potentially_unused_functions"]

    def test_abstractmethod(self):
        """@abstractmethod should not be marked unused."""
        code = '''
from abc import abstractmethod

class Base:
    @abstractmethod
    def do_something(self):
        pass
'''
        result = analyze_python_source(code)
        assert "do_something" in result["decorated_functions"]
        assert "do_something" not in result["potentially_unused_functions"]

    def test_property_decorator(self):
        """@property should not be marked unused."""
        code = '''
class MyClass:
    @property
    def value(self):
        return self._value
'''
        result = analyze_python_source(code)
        assert "value" in result["decorated_functions"]
        assert "value" not in result["potentially_unused_functions"]

    def test_staticmethod(self):
        """@staticmethod should not be marked unused."""
        code = '''
class MyClass:
    @staticmethod
    def helper():
        return 42
'''
        result = analyze_python_source(code)
        assert "helper" in result["decorated_functions"]
        assert "helper" not in result["potentially_unused_functions"]

    def test_classmethod(self):
        """@classmethod should not be marked unused."""
        code = '''
class MyClass:
    @classmethod
    def from_string(cls, s):
        return cls()
'''
        result = analyze_python_source(code)
        assert "from_string" in result["decorated_functions"]
        assert "from_string" not in result["potentially_unused_functions"]


class TestKnownPatterns:
    """Test whitelist of known patterns."""

    def test_dunder_init(self):
        """__init__ should never be marked unused."""
        code = '''
class MyClass:
    def __init__(self):
        pass
'''
        result = analyze_python_source(code)
        assert "__init__" not in result["potentially_unused_functions"]
        assert is_likely_used("__init__")

    def test_dunder_str(self):
        """__str__ should never be marked unused."""
        code = '''
class MyClass:
    def __str__(self):
        return "MyClass"
'''
        result = analyze_python_source(code)
        assert "__str__" not in result["potentially_unused_functions"]

    def test_dunder_enter_exit(self):
        """Context manager dunders should not be marked unused."""
        code = '''
class MyContext:
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
'''
        result = analyze_python_source(code)
        assert "__enter__" not in result["potentially_unused_functions"]
        assert "__exit__" not in result["potentially_unused_functions"]

    def test_post_init(self):
        """__post_init__ (dataclass hook) should not be marked unused."""
        code = '''
from dataclasses import dataclass

@dataclass
class Config:
    name: str
    
    def __post_init__(self):
        self.name = self.name.strip()
'''
        result = analyze_python_source(code)
        assert "__post_init__" not in result["potentially_unused_functions"]

    def test_to_dict(self):
        """to_dict serialization method should not be marked unused."""
        code = '''
class Model:
    def to_dict(self):
        return {"data": self.data}
'''
        result = analyze_python_source(code)
        assert "to_dict" not in result["potentially_unused_functions"]

    def test_from_dict(self):
        """from_dict should not be marked unused."""
        code = '''
class Model:
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
'''
        result = analyze_python_source(code)
        assert "from_dict" not in result["potentially_unused_functions"]

    def test_on_scan_plugin_hook(self):
        """Plugin hooks like on_scan should not be marked unused."""
        code = '''
class MyPlugin:
    def on_scan(self, report):
        pass
    
    def on_analyze(self, summary):
        pass
'''
        result = analyze_python_source(code)
        assert "on_scan" not in result["potentially_unused_functions"]
        assert "on_analyze" not in result["potentially_unused_functions"]

    def test_setup_teardown(self):
        """Test setup/teardown methods should not be marked unused."""
        code = '''
class TestCase:
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
'''
        result = analyze_python_source(code)
        assert "setUp" not in result["potentially_unused_functions"]
        assert "tearDown" not in result["potentially_unused_functions"]


class TestDynamicRegistration:
    """Test detection of dynamic function registration."""

    def test_argparse_set_defaults(self):
        """Functions passed to set_defaults(func=...) should not be marked unused."""
        code = '''
def handle_scan():
    print("Scanning...")

def handle_analyze():
    print("Analyzing...")

parser_scan.set_defaults(func=handle_scan)
parser_analyze.set_defaults(func=handle_analyze)
'''
        result = analyze_python_source(code)
        assert "handle_scan" in result["dynamically_registered"]
        assert "handle_analyze" in result["dynamically_registered"]
        assert "handle_scan" not in result["potentially_unused_functions"]
        assert "handle_analyze" not in result["potentially_unused_functions"]

    def test_add_command(self):
        """Functions passed to add_command should not be marked unused."""
        code = '''
def my_command():
    pass

app.add_command(my_command)
'''
        result = analyze_python_source(code)
        assert "my_command" in result["dynamically_registered"]
        assert "my_command" not in result["potentially_unused_functions"]

    def test_event_subscription(self):
        """Functions passed to subscribe/on should not be marked unused."""
        code = '''
def on_click():
    pass

button.subscribe(on_click)
'''
        result = analyze_python_source(code)
        assert "on_click" in result["dynamically_registered"]
        assert "on_click" not in result["potentially_unused_functions"]

    def test_handler_keyword(self):
        """Functions passed as handler= keyword should be tracked."""
        code = '''
def my_handler():
    pass

register(handler=my_handler)
'''
        result = analyze_python_source(code)
        assert "my_handler" in result["dynamically_registered"]


class TestTrueUnused:
    """Test that truly unused functions are still detected."""

    def test_simple_unused(self):
        """Simple unused function should be detected."""
        code = '''
def unused_function():
    pass

def main():
    print("Hello")

main()
'''
        result = analyze_python_source(code)
        assert "unused_function" in result["potentially_unused_functions"]
        assert "main" not in result["potentially_unused_functions"]

    def test_multiple_unused(self):
        """Multiple unused functions should be detected."""
        code = '''
def orphan_one():
    pass

def orphan_two():
    pass

def used_func():
    pass

used_func()
'''
        result = analyze_python_source(code)
        assert "orphan_one" in result["potentially_unused_functions"]
        assert "orphan_two" in result["potentially_unused_functions"]
        assert "used_func" not in result["potentially_unused_functions"]

    def test_called_function_not_unused(self):
        """Function that is called should not be marked unused."""
        code = '''
def helper():
    return 42

def main():
    result = helper()
    print(result)

main()
'''
        result = analyze_python_source(code)
        assert "helper" not in result["potentially_unused_functions"]
        assert "main" not in result["potentially_unused_functions"]


class TestIsLikelyUsed:
    """Test the is_likely_used helper function."""

    def test_all_dunders_are_likely_used(self):
        """All dunder methods should be likely used."""
        dunders = [
            "__init__", "__new__", "__str__", "__repr__",
            "__enter__", "__exit__", "__call__", "__len__",
            "__getitem__", "__setitem__", "__iter__", "__next__",
        ]
        for name in dunders:
            assert is_likely_used(name), f"{name} should be likely used"

    def test_serialization_methods(self):
        """Serialization convention methods should be likely used."""
        methods = ["to_dict", "from_dict", "to_json", "from_json", "serialize", "deserialize"]
        for name in methods:
            assert is_likely_used(name), f"{name} should be likely used"

    def test_plugin_hooks(self):
        """Plugin hook methods should be likely used."""
        hooks = ["on_scan", "on_analyze", "setup", "teardown", "configure"]
        for name in hooks:
            assert is_likely_used(name), f"{name} should be likely used"

    def test_random_function_not_likely_used(self):
        """Random function names should not be likely used."""
        names = ["my_func", "do_something", "process_data", "calculate_total"]
        for name in names:
            assert not is_likely_used(name), f"{name} should NOT be likely used"


class TestConstants:
    """Test that constants are properly defined."""

    def test_framework_decorators_not_empty(self):
        """FRAMEWORK_DECORATORS should contain entries."""
        assert len(FRAMEWORK_DECORATORS) > 50

    def test_known_patterns_not_empty(self):
        """KNOWN_USED_PATTERNS should contain entries."""
        assert len(KNOWN_USED_PATTERNS) > 100

    def test_dynamic_methods_not_empty(self):
        """DYNAMIC_REGISTRATION_METHODS should contain entries."""
        assert len(DYNAMIC_REGISTRATION_METHODS) >= 5

    def test_set_defaults_in_dynamic(self):
        """set_defaults should be in dynamic registration methods."""
        assert "set_defaults" in DYNAMIC_REGISTRATION_METHODS


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_mixed_decorators_and_calls(self):
        """Mix of decorators, called functions, and unused should be handled."""
        code = '''
@router.get("/health")
def get_health():
    return helper()

def helper():
    return {"status": "ok"}

def unused_orphan():
    pass

def __init__(self):
    pass
'''
        result = analyze_python_source(code)
        
        # get_health: decorated, not unused
        assert "get_health" in result["decorated_functions"]
        assert "get_health" not in result["potentially_unused_functions"]
        
        # helper: called, not unused
        assert "helper" not in result["potentially_unused_functions"]
        
        # unused_orphan: truly unused
        assert "unused_orphan" in result["potentially_unused_functions"]
        
        # __init__: known pattern, not unused
        assert "__init__" not in result["potentially_unused_functions"]

    def test_async_functions(self):
        """Async functions with decorators should be handled."""
        code = '''
@router.post("/scan")
async def scan_project():
    await do_scan()

async def do_scan():
    pass

async def orphan_async():
    pass
'''
        result = analyze_python_source(code)
        assert "scan_project" in result["decorated_functions"]
        assert "scan_project" not in result["potentially_unused_functions"]
        assert "do_scan" not in result["potentially_unused_functions"]
        assert "orphan_async" in result["potentially_unused_functions"]

    def test_nested_decorator_calls(self):
        """Decorators with arguments should be handled."""
        code = '''
@router.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    return Item(id=item_id)

@pytest.mark.parametrize("x", [1, 2, 3])
def test_values(x):
    assert x > 0
'''
        result = analyze_python_source(code)
        assert "get_item" in result["decorated_functions"]
        assert "test_values" in result["decorated_functions"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
