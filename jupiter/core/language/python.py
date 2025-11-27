# jupiter/core/language/python.py
import ast
from typing import Dict, Any, Set

class PythonCodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports: Set[str] = set()
        self.function_calls: Set[str] = set()
        self.defined_functions: Set[str] = set()

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            for alias in node.names:
                self.imports.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.defined_functions.add(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            self.function_calls.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # This is for method calls like 'obj.method()'. It can be complex to resolve 'obj'.
            # For now, I'll just record the attribute name.
            self.function_calls.add(node.func.attr)
        self.generic_visit(node)

def analyze_python_source(source_code: str) -> Dict[str, Any]:
    """
    Analyzes Python source code to extract imports, function definitions, and calls.
    """
    try:
        tree = ast.parse(source_code)
        analyzer = PythonCodeAnalyzer()
        analyzer.visit(tree)

        # Heuristic for potentially unused functions
        potentially_unused = analyzer.defined_functions - analyzer.function_calls

        return {
            "imports": sorted(list(analyzer.imports)),
            "defined_functions": sorted(list(analyzer.defined_functions)),
            "function_calls": sorted(list(analyzer.function_calls)),
            "potentially_unused_functions": sorted(list(potentially_unused)),
        }
    except SyntaxError as e:
        return {"error": f"SyntaxError: {e}"}
