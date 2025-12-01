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


def _merge_adjacent_duplications(duplications: List[Dict], chunk_size: int) -> List[Dict]:
    """Merge overlapping/adjacent duplication clusters into larger blocks.
    
    When a large block of code is duplicated, the sliding window approach creates
    many overlapping detections (e.g., lines 10-15, 11-16, 12-17 all reported separately).
    This function merges them into a single larger block.
    
    Args:
        duplications: Raw list of duplication clusters from chunk detection.
        chunk_size: The chunk size used during detection.
    
    Returns:
        Merged list with adjacent/overlapping duplications combined.
    """
    if not duplications:
        return []
    
    # Group occurrences by file pairs to detect same-file adjacent duplications
    # Key: frozenset of (path, function) pairs -> list of (start_line, end_line, code) per path
    file_pair_groups: Dict[frozenset, Dict[str, List[Tuple[int, int, str]]]] = {}
    
    for dup in duplications:
        occs = dup.get("occurrences", [])
        if len(occs) < 2:
            continue
        
        # Create a signature for this group of files
        file_sig = frozenset((o["path"], o.get("function")) for o in occs)
        
        if file_sig not in file_pair_groups:
            file_pair_groups[file_sig] = {o["path"]: [] for o in occs}
        
        for occ in occs:
            path = occ["path"]
            start_line = occ["line"]
            end_line = occ.get("end_line", start_line + chunk_size - 1)
            code = occ.get("code_excerpt", "")
            file_pair_groups[file_sig][path].append((start_line, end_line, code))
    
    merged_results = []
    
    for file_sig, path_ranges in file_pair_groups.items():
        # For each path, merge overlapping/adjacent ranges
        merged_ranges: Dict[str, List[Tuple[int, int, List[str]]]] = {}
        
        for path, ranges in path_ranges.items():
            if not ranges:
                continue
            
            # Sort by start line
            sorted_ranges = sorted(ranges, key=lambda x: x[0])
            
            # Merge overlapping/adjacent ranges
            merged: List[Tuple[int, int, List[str]]] = []
            current_start, current_end, current_codes = sorted_ranges[0][0], sorted_ranges[0][1], [sorted_ranges[0][2]]
            
            for start, end, code in sorted_ranges[1:]:
                # If this range overlaps or is adjacent (within 1 line), merge
                if start <= current_end + 1:
                    current_end = max(current_end, end)
                    if code not in current_codes:
                        current_codes.append(code)
                else:
                    merged.append((current_start, current_end, current_codes))
                    current_start, current_end, current_codes = start, end, [code]
            
            merged.append((current_start, current_end, current_codes))
            merged_ranges[path] = merged
        
        # Now create merged duplication entries
        # We need to align ranges across files - take ranges that exist in all files
        paths = list(merged_ranges.keys())
        if len(paths) < 2:
            continue
        
        # Simple approach: each merged range in the first file corresponds to a duplication
        first_path = paths[0]
        for idx, (start, end, codes) in enumerate(merged_ranges[first_path]):
            occurrences = []
            
            for path in paths:
                if idx < len(merged_ranges[path]):
                    p_start, p_end, p_codes = merged_ranges[path][idx]
                    # Get the full code excerpt for the merged range
                    full_code = p_codes[0] if p_codes else ""
                    if len(p_codes) > 1:
                        # Try to build extended excerpt from all chunks
                        lines = []
                        for c in p_codes:
                            for line in c.split('\n'):
                                if line not in lines:
                                    lines.append(line)
                        full_code = '\n'.join(lines[:15])  # Limit excerpt length
                        if len(lines) > 15:
                            full_code += f"\n... ({len(lines) - 15} more lines)"
                    
                    # Re-find function name for the merged range start
                    func_name = None
                    for occ in [o for d in duplications for o in d.get("occurrences", []) if o["path"] == path]:
                        if occ["line"] == p_start:
                            func_name = occ.get("function")
                            break
                    
                    occurrences.append({
                        "path": path,
                        "line": p_start,
                        "end_line": p_end,
                        "function": func_name,
                        "code_excerpt": full_code,
                    })
            
            if len(occurrences) >= 2:
                # Create a new hash for the merged block
                merged_hash = hashlib.md5(
                    f"{occurrences[0]['path']}:{occurrences[0]['line']}-{occurrences[0].get('end_line', occurrences[0]['line'])}".encode()
                ).hexdigest()
                
                merged_results.append({
                    "hash": merged_hash,
                    "occurrences": occurrences,
                })
    
    return merged_results


def _is_intentional_mirror(file_path: str, start_line: int, raw_lines: list[str]) -> bool:
    """Check if the duplication is intentionally mirrored (sync comment in docstring nearby).
    
    Looks for patterns like:
    - "mirrors" or "sync" in nearby docstring/comment
    - "keep both in sync" or similar phrases
    
    Args:
        file_path: Path to the file
        start_line: 1-based line number where duplication starts
        raw_lines: All lines of the file
    
    Returns:
        True if this appears to be an intentional mirror, False otherwise.
    """
    # Search in a window before the duplication start (class/function docstring area)
    search_start = max(0, start_line - 20)
    search_end = min(len(raw_lines), start_line + 5)
    
    mirror_patterns = [
        "mirrors",
        "keep both in sync",
        "keep in sync",
        "synchronized with",
        "synced with",
        "# sync:",
        "intentionally duplicated",
    ]
    
    for i in range(search_start, search_end):
        line_lower = raw_lines[i].lower()
        for pattern in mirror_patterns:
            if pattern in line_lower:
                return True
    
    return False


def find_duplications(files: List[Path], chunk_size: int = 6) -> List[Dict[str, object]]:
    """Find duplicated code chunks across files with contextual evidence.

    Args:
        files: List of file paths to check.
        chunk_size: Number of lines to consider as a chunk.

    Returns:
        List of duplication clusters with occurrences including path, line, function, and code excerpt.
    """
    hashes: Dict[str, List[Tuple[str, int, int, str | None, str]]] = {}
    # Store raw lines per file for later mirror detection
    file_lines_cache: Dict[str, list[str]] = {}

    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_lines = [line.rstrip("\n") for line in f.readlines()]
        except (UnicodeDecodeError, OSError):
            continue

        file_lines_cache[str(file_path)] = raw_lines
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
                (
                    str(file_path),
                    chunk_lines[0][1],
                    chunk_lines[-1][1],
                    function_name,
                    code_excerpt,
                )
            )

    # Filter for actual duplications (more than 1 occurrence)
    # Also filter out intentional mirrors (where docstrings indicate sync)
    raw_duplications = []
    for h, occurrences in hashes.items():
        if len(occurrences) > 1:
            # Check if any occurrence is marked as an intentional mirror
            is_intentional = False
            for p, line, _, _, _ in occurrences:
                if p in file_lines_cache:
                    if _is_intentional_mirror(p, line, file_lines_cache[p]):
                        is_intentional = True
                        break
            
            if is_intentional:
                continue  # Skip this duplication cluster
            
            raw_duplications.append(
                {
                    "hash": h,
                    "occurrences": [
                        {
                            "path": p,
                            "line": line,
                            "end_line": end_line,
                            "function": func,
                            "code_excerpt": code,
                        }
                        for p, line, end_line, func, code in occurrences
                    ],
                }
            )

    # Merge adjacent/overlapping duplications into larger blocks
    merged_duplications = _merge_adjacent_duplications(raw_duplications, chunk_size)
    
    # If merging produced results, use them; otherwise fall back to raw (handles edge cases)
    duplications = merged_duplications if merged_duplications else raw_duplications

    # Sort by number of occurrences descending
    duplications.sort(key=lambda x: len(x["occurrences"]), reverse=True)
    return duplications
