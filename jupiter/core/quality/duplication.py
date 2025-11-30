"""Code duplication detection."""

import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

def find_duplications(files: List[Path], chunk_size: int = 6) -> List[Dict[str, object]]:
    """Find duplicated code chunks across files.
    
    Args:
        files: List of file paths to check.
        chunk_size: Number of lines to consider as a chunk.
        
    Returns:
        List of duplication clusters.
    """
    hashes: Dict[str, List[Tuple[str, int]]] = {}
    
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines()]
                
            # Filter empty lines and comments
            code_lines = []
            is_python = str(file_path).endswith(".py")
            comment_prefix = "#" if is_python else "//"
            
            for i, line in enumerate(lines):
                if line and not line.startswith(comment_prefix):
                    code_lines.append((line, i + 1))
            
            if len(code_lines) < chunk_size:
                continue
                
            for i in range(len(code_lines) - chunk_size + 1):
                chunk = "".join([l[0] for l in code_lines[i : i + chunk_size]])
                chunk_hash = hashlib.md5(chunk.encode("utf-8")).hexdigest()
                
                if chunk_hash not in hashes:
                    hashes[chunk_hash] = []
                
                start_line = code_lines[i][1]
                hashes[chunk_hash].append((str(file_path), start_line))
                
        except (UnicodeDecodeError, OSError):
            continue

    # Filter for actual duplications (more than 1 occurrence)
    duplications = []
    for h, occurrences in hashes.items():
        if len(occurrences) > 1:
            # Group by file to avoid counting same file multiple times if not desired,
            # but here we want to see all occurrences.
            duplications.append({
                "hash": h,
                "occurrences": [{"path": p, "line": l} for p, l in occurrences]
            })
            
    # Sort by number of occurrences descending
    duplications.sort(key=lambda x: len(x["occurrences"]), reverse=True)
    return duplications
