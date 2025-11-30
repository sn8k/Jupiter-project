"""Code duplication detection."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple


def _find_enclosing_symbol(lines: list[str], start_index: int, is_python: bool) -> str | None:
    """
    Best-effort heuristic to find the function/method surrounding a duplication start line.

    We scan backwards from the start of the duplicated chunk until we find a pattern that
    resembles a function declaration.
    """
    pattern_py = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)")
    pattern_js = re.compile(r"^\s*(?:function\s+([A-Za-z_][A-Za-z0-9_]*)|([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?(?:function|\(?\s*[^=]*=>))")
    search_window = 80  # limit backwards search to avoid scanning huge files

    for i in range(max(0, start_index - search_window), start_index + 1)[::-1]:
        line = lines[i]
        if is_python:
            match = pattern_py.match(line)
            if match:
                return match.group(1)
        else:
            match = pattern_js.match(line)
            if match:
                # Either group 1 (named function) or group 2 (const fn = ...)
                return match.group(1) or match.group(2)
    return None


def find_duplications(files: List[Path], chunk_size: int = 6) -> List[Dict[str, object]]:
    """Find duplicated code chunks across files with contextual evidence.

    Args:
        files: List of file paths to check.
        chunk_size: Number of lines to consider as a chunk.

    Returns:
        List of duplication clusters with occurrences including path, line, function, and code excerpt.
    """
    hashes: Dict[str, List[Tuple[str, int, str | None, str]]] = {}

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_lines = [line.rstrip("\n") for line in f.readlines()]
        except (UnicodeDecodeError, OSError):
            continue

        is_python = str(file_path).endswith(".py")
        comment_prefix = "#" if is_python else "//"

        # Filter empty lines and comments but keep original line content and indices
        code_lines: list[Tuple[str, int]] = []
        for idx, raw_line in enumerate(raw_lines):
            if raw_line.strip() and not raw_line.strip().startswith(comment_prefix):
                code_lines.append((raw_line, idx + 1))

        if len(code_lines) < chunk_size:
            continue

        for i in range(len(code_lines) - chunk_size + 1):
            chunk_lines = code_lines[i : i + chunk_size]
            normalized = "".join(l[0].strip() for l in chunk_lines)
            chunk_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()

            start_line_index = chunk_lines[0][1] - 1  # zero-based for list access
            function_name = _find_enclosing_symbol(raw_lines, start_line_index, is_python)
            code_excerpt = "\n".join(line for line, _ in chunk_lines)

            hashes.setdefault(chunk_hash, []).append(
                (str(file_path), chunk_lines[0][1], function_name, code_excerpt)
            )

    # Filter for actual duplications (more than 1 occurrence)
    duplications = []
    for h, occurrences in hashes.items():
        if len(occurrences) > 1:
            duplications.append(
                {
                    "hash": h,
                    "occurrences": [
                        {
                            "path": p,
                            "line": line,
                            "function": func,
                            "code_excerpt": code,
                        }
                        for p, line, func, code in occurrences
                    ],
                }
            )

    # Sort by number of occurrences descending
    duplications.sort(key=lambda x: len(x["occurrences"]), reverse=True)
    return duplications
