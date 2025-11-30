import re
from typing import Dict, Any, Set, List

def analyze_js_ts_source(source_code: str) -> Dict[str, Any]:
    """
    Analyzes JavaScript/TypeScript source code to extract imports and function definitions.
    Uses regex heuristics.
    """
    imports: Set[str] = set()
    defined_functions: Set[str] = set()
    
    # Regex patterns
    # Import ES6: import ... from "..."
    # We try to capture the module path
    import_pattern = re.compile(r'import\s+.*?from\s+[\'"](.*?)[\'"]')
    # Import CommonJS: require("...")
    require_pattern = re.compile(r'require\s*\(\s*[\'"](.*?)[\'"]\s*\)')
    
    # Function definitions
    # function foo()
    func_decl_pattern = re.compile(r'function\s+([a-zA-Z0-9_$]+)\s*\(')
    # const foo = () =>
    arrow_func_pattern = re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\(?.*?\)?\s*=>')
    # const foo = function()
    var_func_pattern = re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?function')
    # class method (simplified) - looks for identifier followed by ( and {
    # We use MULTILINE to match start of lines (ignoring indentation)
    method_pattern = re.compile(r'^\s*(?:async\s+)?([a-zA-Z0-9_$]+)\s*\(.*?\)\s*\{', re.MULTILINE)

    # Extract imports
    for match in import_pattern.finditer(source_code):
        imports.add(match.group(1))
    for match in require_pattern.finditer(source_code):
        imports.add(match.group(1))

    # Extract functions
    for match in func_decl_pattern.finditer(source_code):
        defined_functions.add(match.group(1))
    for match in arrow_func_pattern.finditer(source_code):
        defined_functions.add(match.group(1))
    for match in var_func_pattern.finditer(source_code):
        defined_functions.add(match.group(1))
    for match in method_pattern.finditer(source_code):
        name = match.group(1)
        # Filter out common control flow keywords that might look like methods
        if name not in ['if', 'for', 'while', 'switch', 'catch', 'constructor']:
             defined_functions.add(name)

    return {
        "imports": list(sorted(imports)),
        "defined_functions": list(sorted(defined_functions)),
        "function_calls": [], # Hard to do reliably with regex without AST
        "potentially_unused_functions": [] # Cannot determine without full AST/references
    }
