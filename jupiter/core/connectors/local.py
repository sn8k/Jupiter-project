import asyncio
from typing import Any, Dict, Optional
from pathlib import Path
from jupiter.core.connectors.base import BaseConnector
from jupiter.core.scanner import ProjectScanner
from jupiter.core.runner import run_command
from jupiter.core.cache import CacheManager
from jupiter.core.analyzer import ProjectAnalyzer

class LocalConnector(BaseConnector):
    """Connector for local filesystem projects."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()

    async def scan(self, options: Dict[str, Any]) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_scan_sync, options)

    def _run_scan_sync(self, options: Dict[str, Any]) -> Dict[str, Any]:
        scanner = ProjectScanner(
            root=self.root_path,
            ignore_hidden=not options.get("show_hidden", False),
            ignore_globs=options.get("ignore_globs"),
            incremental=options.get("incremental", False),
        )
        
        files = list(scanner.iter_files())
        
        # Convert to dicts for the report
        file_dicts = []
        for m in files:
            file_dicts.append({
                "path": str(m.path),
                "size_bytes": m.size_bytes,
                "modified_timestamp": m.modified_timestamp,
                "file_type": m.file_type,
                "language_analysis": m.language_analysis,
            })

        report = {
            "report_schema_version": "1.0",
            "root": str(self.root_path),
            "files": file_dicts,
            "dynamic": None,
            "plugins": {}, # Plugins info should be injected by the caller
        }
        
        # Save to cache
        cache_manager = CacheManager(self.root_path)
        cache_manager.save_last_scan(report)
        
        return report

    async def analyze(self, options: Dict[str, Any]) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_analyze_sync, options)

    def _run_analyze_sync(self, options: Dict[str, Any]) -> Dict[str, Any]:
        scanner = ProjectScanner(
            root=self.root_path,
            ignore_hidden=not options.get("show_hidden", False),
            ignore_globs=options.get("ignore_globs"),
        )
        analyzer = ProjectAnalyzer(root=self.root_path)
        summary = analyzer.summarize(scanner.iter_files(), top_n=options.get("top", 5))
        return summary.to_dict()

    async def run_command(self, command: list[str], with_dynamic: bool = False) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, 
            run_command, 
            command, 
            self.root_path, 
            with_dynamic
        )
        
        if result.dynamic_data:
            # Merge into cache
            await loop.run_in_executor(None, self._merge_dynamic_data, result.dynamic_data)
            
        return result.dict()

    def _merge_dynamic_data(self, dynamic_data: Dict[str, Any]):
        cache_manager = CacheManager(self.root_path)
        last_scan = cache_manager.load_last_scan()
        if last_scan:
            if "dynamic" not in last_scan or last_scan["dynamic"] is None:
                last_scan["dynamic"] = {"calls": {}, "times": {}, "call_graph": {}}
            
            # Ensure structure is correct
            if "calls" not in last_scan["dynamic"]:
                old_calls = last_scan["dynamic"] if isinstance(last_scan["dynamic"], dict) else {}
                last_scan["dynamic"] = {"calls": old_calls, "times": {}, "call_graph": {}}

            # Merge calls
            current_calls = last_scan["dynamic"].get("calls", {})
            new_calls = dynamic_data.get("calls", {})
            for func, count in new_calls.items():
                current_calls[func] = current_calls.get(func, 0) + count
            last_scan["dynamic"]["calls"] = current_calls

            # Merge times
            current_times = last_scan["dynamic"].get("times", {})
            new_times = dynamic_data.get("times", {})
            for func, time_val in new_times.items():
                current_times[func] = current_times.get(func, 0.0) + time_val
            last_scan["dynamic"]["times"] = current_times

            # Merge call graph
            current_graph = last_scan["dynamic"].get("call_graph", {})
            new_graph = dynamic_data.get("call_graph", {})
            for caller, callees in new_graph.items():
                if caller not in current_graph:
                    current_graph[caller] = {}
                for callee, count in callees.items():
                    current_graph[caller][callee] = current_graph[caller].get(callee, 0) + count
            last_scan["dynamic"]["call_graph"] = current_graph

            cache_manager.save_last_scan(last_scan)

    def get_api_base_url(self) -> Optional[str]:
        return None
