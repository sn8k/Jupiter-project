"""Project scanning utilities."""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
from pathlib import Path
from typing import Iterable, Iterator, Optional, Dict, Any, Callable
import logging
import time
import concurrent.futures

from jupiter.core.language.python import analyze_python_source
from jupiter.core.language.js_ts import analyze_js_ts_source
from jupiter.core.cache import CacheManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class FileMetadata:
    """Basic metadata describing a discovered file."""

    path: Path
    size_bytes: int
    modified_timestamp: float
    file_type: str
    language_analysis: Optional[Dict[str, Any]] = None

    @classmethod
    def from_path(cls, path: Path) -> "FileMetadata":
        """Create :class:`FileMetadata` from a filesystem path."""

        return cls(
            path=path,
            size_bytes=path.stat().st_size,
            modified_timestamp=path.stat().st_mtime,
            file_type=path.suffix.lower().lstrip("."),
        )


class ProjectScanner:
    """Scan a project directory to enumerate files."""

    VOLATILE_EXTENSIONS = {".tmp", ".log", ".bak", ".swp", ".pyc"}
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(
        self,
        root: Path,
        ignore_hidden: bool = True,
        ignore_globs: list[str] | None = None,
        ignore_file: str = ".jupiterignore",
        incremental: bool = False,
        no_cache: bool = False,
        perf_mode: bool = False,
        max_workers: int | None = None,
        large_file_threshold: int = 10 * 1024 * 1024,
        progress_callback: Callable[[str, Dict[str, Any]], None] | None = None,
    ) -> None:
        self.root = root
        self.ignore_hidden = ignore_hidden
        self.ignore_patterns = self._resolve_ignore_patterns(ignore_globs, ignore_file)
        self.incremental = incremental
        self.no_cache = no_cache
        self.perf_mode = perf_mode
        self.max_workers = max_workers
        self.large_file_threshold = large_file_threshold
        self.progress_callback = progress_callback
        self.cache_manager = CacheManager(root)
        self.cached_files: Dict[str, Dict[str, Any]] = {}
        
        if self.no_cache:
            self.cache_manager.clear_cache()
        elif self.incremental:
            self._load_cache()

    def _load_cache(self):
        """Load previous scan results for incremental scanning."""
        last_scan = self.cache_manager.load_last_scan()
        if last_scan and "files" in last_scan:
            for f in last_scan["files"]:
                self.cached_files[f["path"]] = f

    DEFAULT_IGNORES = [
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        "node_modules",
        "dist",
        "build",
        "*.egg-info",
    ]

    def iter_files(self) -> Iterator[FileMetadata]:
        """Yield :class:`FileMetadata` objects for files under ``root``."""
        start_time = time.time()
        
        # Collect all paths first to allow parallel processing
        paths = list(self._walk_files(self.root))
        total_files = len(paths)
        
        walk_time = time.time() - start_time
        if self.perf_mode:
            logger.info(f"Walked {len(paths)} files in {walk_time:.4f}s")

        # Emit initial progress
        if self.progress_callback:
            self.progress_callback("SCAN_PROGRESS", {
                "phase": "scanning",
                "total_files": total_files,
                "processed": 0,
                "percent": 0
            })

        processed_count = 0
        
        # Use ThreadPoolExecutor for parallel processing
        # IO-bound tasks (reading files) benefit from threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and keep track of futures
            future_to_path = {executor.submit(self._process_single_file, path): path for path in paths}
            
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                processed_count += 1
                
                try:
                    result = future.result()
                    
                    # Emit progress for each file
                    if self.progress_callback:
                        percent = int((processed_count / total_files) * 100) if total_files > 0 else 100
                        self.progress_callback("SCAN_FILE_COMPLETED", {
                            "file": str(path.relative_to(self.root)),
                            "processed": processed_count,
                            "total": total_files,
                            "percent": percent,
                            "has_analysis": result is not None and result.language_analysis is not None
                        })
                    
                    if result:
                        yield result
                        
                except Exception as e:
                    logger.warning(f"Failed to process file {path}: {e}")
                    if self.progress_callback:
                        self.progress_callback("SCAN_FILE_COMPLETED", {
                            "file": str(path.relative_to(self.root)),
                            "processed": processed_count,
                            "total": total_files,
                            "percent": int((processed_count / total_files) * 100) if total_files > 0 else 100,
                            "error": str(e)
                        })

        if self.perf_mode:
            total_time = time.time() - start_time
            logger.info(f"Scanned {len(paths)} files in {total_time:.4f}s")

    def _process_single_file(self, path: Path) -> Optional[FileMetadata]:
        """Process a single file and return its metadata."""
        try:
            metadata = FileMetadata.from_path(path)
            relative_path = str(path.relative_to(self.root))
            
            # Check cache if incremental
            cached = None
            is_volatile = path.suffix.lower() in self.VOLATILE_EXTENSIONS

            if self.incremental and not is_volatile:
                cached = self.cached_files.get(str(path))
            
            if (
                cached 
                and cached["modified_timestamp"] == metadata.modified_timestamp 
                and cached["size_bytes"] == metadata.size_bytes
            ):
                # Use cached analysis
                metadata.language_analysis = cached.get("language_analysis")
                # Emit event for functions found in cache
                if self.progress_callback and metadata.language_analysis:
                    # Python uses 'defined_functions', JS/TS uses 'functions'
                    funcs = metadata.language_analysis.get("defined_functions", []) or metadata.language_analysis.get("functions", [])
                    classes = metadata.language_analysis.get("classes", [])
                    func_count = len(funcs) if isinstance(funcs, (list, set)) else 0
                    class_count = len(classes) if isinstance(classes, (list, set)) else 0
                    if func_count > 0 or class_count > 0:
                        func_names = list(funcs)[:5] if isinstance(funcs, (list, set)) else []
                        self.progress_callback("FUNCTION_ANALYZED", {
                            "file": relative_path,
                            "functions_count": func_count,
                            "classes_count": class_count,
                            "functions": func_names,
                            "from_cache": True
                        })
            elif metadata.file_type == "py":
                if metadata.size_bytes > self.large_file_threshold:
                    metadata.language_analysis = {"error": "File too large to analyze"}
                else:
                    try:
                        source = path.read_text(encoding="utf-8")
                        metadata.language_analysis = analyze_python_source(source)
                        # Emit event for analyzed functions
                        if self.progress_callback and metadata.language_analysis:
                            # Python analyzer returns 'defined_functions' as a set
                            funcs = metadata.language_analysis.get("defined_functions", [])
                            func_count = len(funcs) if isinstance(funcs, (list, set)) else 0
                            if func_count > 0:
                                func_names = list(funcs)[:5] if isinstance(funcs, (list, set)) else []
                                self.progress_callback("FUNCTION_ANALYZED", {
                                    "file": relative_path,
                                    "functions_count": func_count,
                                    "classes_count": 0,
                                    "functions": func_names,
                                    "from_cache": False
                                })
                    except Exception as e:
                        metadata.language_analysis = {"error": f"Could not read or parse file: {e}"}
            elif metadata.file_type in ("js", "ts", "jsx", "tsx"):
                if metadata.size_bytes > self.large_file_threshold:
                    metadata.language_analysis = {"error": "File too large to analyze"}
                else:
                    try:
                        source = path.read_text(encoding="utf-8")
                        metadata.language_analysis = analyze_js_ts_source(source)
                        # Emit event for analyzed functions
                        if self.progress_callback and metadata.language_analysis:
                            # JS/TS analyzer also returns 'defined_functions' as a list
                            funcs = metadata.language_analysis.get("defined_functions", [])
                            func_count = len(funcs) if isinstance(funcs, (list, set)) else 0
                            if func_count > 0:
                                func_names = list(funcs)[:5] if isinstance(funcs, (list, set)) else []
                                self.progress_callback("FUNCTION_ANALYZED", {
                                    "file": relative_path,
                                    "functions_count": func_count,
                                    "classes_count": 0,
                                    "functions": func_names,
                                    "from_cache": False
                                })
                    except Exception as e:
                        metadata.language_analysis = {"error": f"Could not read or parse file: {e}"}
            
            return metadata
        except Exception as e:
            logger.warning(f"Failed to process file {path}: {e}")
            return None

    def _walk_files(self, root: Path) -> Iterable[Path]:
        """Iterate over files respecting ignore rules."""
        import os

        # logger.info(f"Walking files in {root}. Ignore patterns: {self.ignore_patterns}")

        for dirpath, dirnames, filenames in os.walk(root):
            # In-place modification of dirnames to prune traversal
            
            # 1. Remove hidden directories if enabled
            if self.ignore_hidden:
                original_len = len(dirnames)
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                # if len(dirnames) < original_len:
                #     logger.debug(f"Pruned hidden dirs in {dirpath}")
            
            current_path = Path(dirpath)
            try:
                rel_path = current_path.relative_to(root)
            except ValueError:
                rel_path = Path(".")

            # 2. Remove ignored directories
            # We iterate backwards to safely remove
            for i in range(len(dirnames) - 1, -1, -1):
                d = dirnames[i]
                
                # Check name match (e.g. "venv", "node_modules")
                # We use fnmatch on the name directly
                if any(fnmatch.fnmatch(d, p) for p in self.ignore_patterns):
                    # logger.debug(f"Ignoring dir (name match): {d} in {dirpath}")
                    del dirnames[i]
                    continue
                
                # Check path match (e.g. "src/ignored_dir")
                d_rel = rel_path / d
                if self._should_ignore(d_rel):
                    # logger.debug(f"Ignoring dir (path match): {d_rel}")
                    del dirnames[i]
                    continue

            for f in filenames:
                if self.ignore_hidden and f.startswith("."):
                    continue
                
                # Check name match
                if any(fnmatch.fnmatch(f, p) for p in self.ignore_patterns):
                    continue

                f_rel = rel_path / f
                if self._should_ignore(f_rel):
                    continue
                
                yield current_path / f

    def _should_ignore(self, relative_path: Path) -> bool:
        """Return whether a path should be skipped based on ignore patterns."""

        relative_str = relative_path.as_posix()
        return any(fnmatch.fnmatch(relative_str, pattern) for pattern in self.ignore_patterns)

    def _resolve_ignore_patterns(self, patterns: list[str] | None, ignore_file: str) -> list[str]:
        """Load ignore patterns from an ignore file and explicit arguments.

        If an ignore file exists at the project root, its patterns are loaded.
        Any patterns passed via the ``patterns`` argument are then appended to
        this list.
        """

        all_patterns: list[str] = []
        ignore_path = self.root / ignore_file
        if ignore_path.exists():
            for line in ignore_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                # Normalize directory patterns (e.g. "dir/" -> "dir")
                if stripped.endswith("/"):
                    stripped = stripped.rstrip("/")
                all_patterns.append(stripped)

        if patterns is not None:
            all_patterns.extend(patterns)

        # Add default ignores
        all_patterns.extend(self.DEFAULT_IGNORES)

        return all_patterns
