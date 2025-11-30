"""Cyclomatic complexity estimation."""

import ast
from pathlib import Path

def estimate_complexity(file_path: Path) -> int:
    """Estimate cyclomatic complexity of a Python file.
    
    This is a naive implementation that counts branching statements.
    It does not parse the full AST depth but iterates over nodes.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        
        tree = ast.parse(source)
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
                
        return complexity
    except (SyntaxError, UnicodeDecodeError):
        return 0
    except Exception:
        return 0


def estimate_js_complexity(file_path: Path) -> int:
    """Estimate cyclomatic complexity of a JS/TS file using regex heuristics."""
    import re
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
            
        complexity = 1
        
        # Control flow keywords
        # We match whole words to avoid matching inside variable names
        keywords = [
            r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\bcase\b', r'\bcatch\b'
        ]
        
        for kw in keywords:
            complexity += len(re.findall(kw, source))
            
        # Operators
        operators = [
            r'&&', r'\|\|', r'\?'
        ]
        
        for op in operators:
            complexity += len(re.findall(op, source))
            
        return complexity
    except Exception:
        return 0
