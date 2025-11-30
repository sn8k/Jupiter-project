"""Simulation of code changes and their impact."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

from jupiter.core.scanner import FileMetadata


@dataclass
class Impact:
    target: str  # File path or "File::Function"
    impact_type: str  # "broken_import", "broken_call", "orphan"
    details: str
    severity: str  # "high", "medium", "low"


@dataclass
class SimulationResult:
    target: str
    impacts: List[Impact]
    risk_score: str  # "high", "medium", "low"


class ProjectSimulator:
    """Simulates changes in the project to predict impact."""

    def __init__(self, files: List[Dict[str, Any]]):
        """
        Initialize with a list of file dictionaries (from scan report).
        We use dicts because that's what the API/CLI usually passes around after scanning.
        """
        self.files = files
        self.file_map = {f["path"]: f for f in files}
        
        # Build indices
        self.defined_functions: Dict[str, str] = {}  # func_name -> file_path
        self.imports_by_file: Dict[str, Set[str]] = {}  # file_path -> set of imported names
        self.calls_by_file: Dict[str, Set[str]] = {}  # file_path -> set of called function names
        
        self._build_indices()

    def _build_indices(self):
        for f in self.files:
            path = f["path"]
            lang_analysis = f.get("language_analysis") or {}
            
            # Index defined functions (heuristic: last writer wins for duplicates, or we could store list)
            # For better accuracy, we'd need fully qualified names, but we'll stick to simple names for now
            # as per the current analyzer capabilities.
            for func in lang_analysis.get("defined_functions", []):
                # We store a mapping of function name to defining file. 
                # Issue: multiple files can define the same function name.
                # We'll store a list of files defining it? Or just rely on imports?
                # Let's try to be slightly smarter: we only care about global uniqueness if we don't check imports.
                # But we should check imports.
                pass

            self.imports_by_file[path] = set(lang_analysis.get("imports", []))
            self.calls_by_file[path] = set(lang_analysis.get("function_calls", []))

    def simulate_remove_file(self, file_path: str) -> SimulationResult:
        """Simulate removing a file."""
        impacts = []
        
        # 1. Check for broken imports
        # Heuristic: if file B imports something that looks like file_path's module name
        # We need to convert file path to module notation (e.g. jupiter/core/scanner.py -> jupiter.core.scanner)
        module_name = self._path_to_module(file_path)
        
        for other_path, imports in self.imports_by_file.items():
            if other_path == file_path:
                continue
                
            # Check if other_path imports this module
            # Exact match or sub-module match
            for imp in imports:
                if imp == module_name or imp.startswith(f"{module_name}."):
                    impacts.append(Impact(
                        target=other_path,
                        impact_type="broken_import",
                        details=f"Imports removed module '{imp}'",
                        severity="high"
                    ))

        # 2. Check for broken calls (functions defined in this file)
        target_file = self.file_map.get(file_path)
        if target_file:
            defined_funcs = target_file.get("language_analysis", {}).get("defined_functions", [])
            for func in defined_funcs:
                # For each function defined in the removed file, see who calls it
                # This is tricky without full resolution. 
                # We'll assume if B calls 'func' AND B imports 'module_name', it's a hit.
                for other_path, calls in self.calls_by_file.items():
                    if other_path == file_path:
                        continue
                    
                    if func in calls:
                        # Check if it likely imports it
                        other_imports = self.imports_by_file.get(other_path, set())
                        if any(imp == module_name or imp.startswith(f"{module_name}") for imp in other_imports):
                             impacts.append(Impact(
                                target=f"{other_path}::{func}", # Approximate location
                                impact_type="broken_call",
                                details=f"Calls function '{func}' from removed file",
                                severity="high"
                            ))

        return self._finalize_result(f"Remove file {file_path}", impacts)

    def simulate_remove_function(self, file_path: str, function_name: str) -> SimulationResult:
        """Simulate removing a function from a file."""
        impacts = []
        module_name = self._path_to_module(file_path)

        # Check who calls this function
        for other_path, calls in self.calls_by_file.items():
            if function_name in calls:
                # If it's the same file, it's a broken internal call
                if other_path == file_path:
                     impacts.append(Impact(
                        target=other_path,
                        impact_type="broken_internal_call",
                        details=f"Internal call to removed function '{function_name}'",
                        severity="high"
                    ))
                     continue

                # If it's another file, check if it imports the module
                other_imports = self.imports_by_file.get(other_path, set())
                if any(imp == module_name or imp.startswith(f"{module_name}") for imp in other_imports):
                    impacts.append(Impact(
                        target=other_path,
                        impact_type="broken_call",
                        details=f"Calls removed function '{function_name}'",
                        severity="high"
                    ))

        return self._finalize_result(f"Remove function {file_path}::{function_name}", impacts)

    def _path_to_module(self, path: str) -> str:
        """Convert file path to python module notation."""
        p = Path(path)
        # Remove extension
        name = p.with_suffix("").as_posix()
        # Replace slashes with dots
        return name.replace("/", ".")

    def _finalize_result(self, target: str, impacts: List[Impact]) -> SimulationResult:
        risk = "low"
        if any(i.severity == "high" for i in impacts):
            risk = "high"
        elif any(i.severity == "medium" for i in impacts):
            risk = "medium"
            
        return SimulationResult(target=target, impacts=impacts, risk_score=risk)
