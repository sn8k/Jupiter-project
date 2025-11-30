"""Command line entrypoint for Jupiter."""

from __future__ import annotations

import argparse
import json
import logging
import time
import sys
import threading
import webbrowser
from dataclasses import asdict
from pathlib import Path

from jupiter import __version__
from jupiter.config import load_config, PluginsConfig, PerformanceConfig
from jupiter.core import ProjectAnalyzer, ProjectScanner, ScanReport
from jupiter.core.cache import CacheManager
from jupiter.core.history import HistoryManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.state import load_last_root, save_last_root
from jupiter.core.updater import apply_update
from jupiter.server import JupiterAPIServer
from jupiter.web import launch_web_ui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _clean_root_argument(root: Path | None) -> Path | None:
    """Return a sanitized path if the CLI argument was provided."""
    if root is None:
        return None
    return Path(str(root).strip('"\''))


def resolve_root_argument(root_arg: Path | None) -> Path:
    """Resolve the active root, using persisted state if none is explicitly provided."""
    explicit_root = _clean_root_argument(root_arg)
    if explicit_root:
        return explicit_root
    remembered = load_last_root()
    if remembered:
        return remembered
    return Path.cwd()


def handle_update(source: str, force: bool = False) -> None:
    """Handle self-update."""
    try:
        apply_update(source, force)
    except Exception as e:
        logger.error("Update failed: %s", e)
        if not force:
            return


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Jupiter project inspection tool")
    parser.add_argument("--version", action="version", version=f"jupiter {__version__}")
    parser.add_argument("--root", type=Path, default=None, help="Project root (optional, overrides current directory)")
    
    # Global root argument (optional, for when no subcommand is used)
    # Note: This might be tricky with subcommands. 
    # For now, we rely on subcommands having their own root arg.
    # If no subcommand is provided, we assume CWD or we can try to parse it.
    
    subcommands = parser.add_subparsers(dest="command", required=False)

    # Update command
    update_parser = subcommands.add_parser("update", help="Update Jupiter")
    update_parser.add_argument("source", help="Source for update (git URL or path to ZIP)")
    update_parser.add_argument("--force", action="store_true", help="Force update even on error")

    scan_parser = subcommands.add_parser("scan", help="Scan a project directory")
    scan_parser.add_argument("root", type=Path, nargs="?", default=None, help="Root folder to scan")
    scan_parser.add_argument("--show-hidden", action="store_true", help="Include hidden files")
    scan_parser.add_argument(
        "--ignore",
        action="append",
        dest="ignore_globs",
        default=None,
        help="Glob pattern to ignore (can be provided multiple times)",
    )
    scan_parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the JSON report to instead of stdout",
    )
    scan_parser.add_argument("--incremental", action="store_true", help="Use incremental scanning")
    scan_parser.add_argument("--no-cache", action="store_true", help="Force scan without using cache")
    scan_parser.add_argument("--perf", action="store_true", help="Enable performance profiling")

    analyze_parser = subcommands.add_parser("analyze", help="Analyze a project directory")
    analyze_parser.add_argument("root", type=Path, nargs="?", default=None, help="Root folder to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="Emit the summary as JSON")
    analyze_parser.add_argument("--perf", action="store_true", help="Enable performance profiling")
    scan_parser.add_argument("--no-snapshot", action="store_true", help="Skip automatic snapshot creation")
    scan_parser.add_argument("--snapshot-label", help="Override the generated snapshot label")
    analyze_parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Number of largest files to include in the summary",
    )
    analyze_parser.add_argument(
        "--ignore",
        action="append",
        dest="ignore_globs",
        default=None,
        help="Glob pattern to ignore during analysis",
    )
    analyze_parser.add_argument("--show-hidden", action="store_true", help="Include hidden files in analysis")
    analyze_parser.add_argument("--incremental", action="store_true", help="Use incremental scanning")
    analyze_parser.add_argument("--no-cache", action="store_true", help="Force analysis without using cache")

    ci_parser = subcommands.add_parser("ci", help="Run in CI mode with quality gates")
    ci_parser.add_argument("root", type=Path, nargs="?", default=None, help="Root folder to analyze")
    ci_parser.add_argument("--json", action="store_true", help="Emit the summary as JSON")
    ci_parser.add_argument("--fail-on-complexity", type=int, help="Override max complexity threshold")
    ci_parser.add_argument("--fail-on-duplication", type=int, help="Override max duplication clusters threshold")
    ci_parser.add_argument("--fail-on-unused", type=int, help="Override max unused functions threshold")

    server_parser = subcommands.add_parser("server", help="Start the API server")
    server_parser.add_argument("root", type=Path, nargs="?", default=None, help="Project root to serve")
    server_parser.add_argument("--host", help="Host to bind")
    server_parser.add_argument("--port", type=int, help="Port to bind")

    run_parser = subcommands.add_parser("run", help="Run a command with optional dynamic analysis")
    run_parser.add_argument("command_str", help="Command to run (e.g. 'python script.py')")
    run_parser.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    run_parser.add_argument("--with-dynamic", action="store_true", help="Enable dynamic analysis")

    gui_parser = subcommands.add_parser("gui", help="Lancer l'interface web locale")
    gui_parser.add_argument("root", type=Path, nargs="?", default=None, help="Projet à afficher dans la GUI")
    gui_parser.add_argument("--host", help="Hôte HTTP pour la GUI")
    gui_parser.add_argument("--port", type=int, help="Port HTTP pour la GUI")

    watch_parser = subcommands.add_parser("watch", help="Watch a project directory for changes")
    watch_parser.add_argument("root", type=Path, nargs="?", default=None, help="Root folder to watch")

    snapshots_parser = subcommands.add_parser("snapshots", help="Inspect saved scan snapshots")
    snapshots_sub = snapshots_parser.add_subparsers(dest="snapshot_command", required=True)

    snap_list = snapshots_sub.add_parser("list", help="List available snapshots")
    snap_list.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    snap_list.add_argument("--json", action="store_true", help="Output as JSON")

    snap_show = snapshots_sub.add_parser("show", help="Show a snapshot's metadata or report")
    snap_show.add_argument("snapshot_id", help="Snapshot identifier")
    snap_show.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    snap_show.add_argument("--report", action="store_true", help="Include the full report payload")
    snap_show.add_argument("--json", action="store_true", help="Output as JSON")

    snap_diff = snapshots_sub.add_parser("diff", help="Diff two snapshots")
    snap_diff.add_argument("snapshot_a", help="Older snapshot identifier")
    snap_diff.add_argument("snapshot_b", help="Newer snapshot identifier")
    snap_diff.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    snap_diff.add_argument("--json", action="store_true", help="Output as JSON")

    simulate_parser = subcommands.add_parser("simulate", help="Simulate changes")
    simulate_sub = simulate_parser.add_subparsers(dest="simulate_command", required=True)
    
    sim_remove = simulate_sub.add_parser("remove", help="Simulate removal of a file or function")
    sim_remove.add_argument("target", help="Target path (file) or path::function")
    sim_remove.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    sim_remove.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def handle_scan(
    root: Path,
    show_hidden: bool,
    ignore_globs: list[str] | None,
    incremental: bool,
    no_cache: bool,
    plugins_config: PluginsConfig | None = None,
    performance_config: PerformanceConfig | None = None,
    snapshot_label: str | None = None,
    snapshot_enabled: bool = True,
    backend_name: str | None = None,
    perf_mode: bool = False,
) -> str:
    """Run a filesystem scan and return a JSON report."""
    logger.info("Scanning project at %s", root)
    
    # Load plugins
    plugin_manager = PluginManager(config=plugins_config)
    plugin_manager.discover_and_load()
    
    scanner = ProjectScanner(
        root=root, 
        ignore_hidden=not show_hidden, 
        ignore_globs=ignore_globs,
        incremental=incremental,
        no_cache=no_cache,
        perf_mode=perf_mode,
        max_workers=performance_config.max_workers if performance_config else None,
        large_file_threshold=performance_config.large_file_threshold if performance_config else 10 * 1024 * 1024,
    )
    report = ScanReport.from_files(root=root, files=scanner.iter_files())
    
    # Convert to dict for plugins and output
    report_dict = report.to_dict()
    
    # Add plugins info to report
    report_dict["plugins"] = plugin_manager.get_plugins_info()
    
    # Run plugin hooks
    plugin_manager.hook_on_scan(report_dict)
    
    # Save to cache
    cache_manager = CacheManager(root)
    cache_manager.save_last_scan(report_dict)

    if snapshot_enabled:
        try:
            history = HistoryManager(root)
            metadata = history.create_snapshot(
                report_dict,
                label=snapshot_label,
                backend_name=backend_name,
            )
            logger.info("Snapshot saved as %s", metadata.id)
        except Exception as exc:
            logger.warning("Failed to store snapshot: %s", exc)
    
    payload = json.dumps(report_dict, indent=2)
    return payload


def handle_snapshot_list(root: Path, as_json: bool) -> None:
    history = HistoryManager(root)
    snapshots = history.list_snapshots()
    if as_json:
        print(json.dumps([asdict(s) for s in snapshots], indent=2))
        return

    if not snapshots:
        print("No snapshots recorded yet.")
        return

    for meta in snapshots:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta.timestamp))
        print(f"{meta.id}\t{meta.label}\t{ts}\tfiles={meta.file_count}\tsize={meta.total_size_bytes}B")


def handle_snapshot_show(root: Path, snapshot_id: str, include_report: bool, as_json: bool) -> None:
    history = HistoryManager(root)
    snapshot = history.get_snapshot(snapshot_id)
    if not snapshot:
        logger.error("Snapshot %s not found", snapshot_id)
        raise SystemExit(1)

    payload = snapshot if include_report else {"metadata": snapshot["metadata"]}
    if as_json:
        print(json.dumps(payload, indent=2))
        return

    meta = payload["metadata"]
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(meta["timestamp"]))
    print(f"Snapshot {meta['id']} ({meta['label']})")
    print(f" Created: {ts}")
    print(f" Files: {meta['file_count']} | Size: {meta['total_size_bytes']} bytes")
    print(f" Functions: {meta.get('function_count', 0)} | Potentially unused: {meta.get('unused_function_count', 0)}")
    if include_report:
        print("--- Report excerpt ---")
        file_count = len(snapshot.get("report", {}).get("files", []))
        print(f" Report root: {snapshot.get('report', {}).get('root', '<unknown>')} ({file_count} files)")


def handle_snapshot_diff(root: Path, snapshot_a: str, snapshot_b: str, as_json: bool) -> None:
    history = HistoryManager(root)
    diff = history.compare_snapshots(snapshot_a, snapshot_b).to_dict()
    if as_json:
        print(json.dumps(diff, indent=2))
        return

    summary = diff["diff"]["metrics_delta"]
    print(f"Diff {snapshot_a} -> {snapshot_b}")
    print(f" File delta: {summary['file_count']} | Size delta: {summary['total_size_bytes']} bytes")
    print(f" Functions delta: {summary['function_count']} | Unused delta: {summary['unused_function_count']}")
    files = diff["diff"]
    print(f" Added files: {len(files['files_added'])}, Removed: {len(files['files_removed'])}, Modified: {len(files['files_modified'])}")


def handle_analyze(root: Path, as_json: bool, top: int, ignore_globs: list[str] | None, show_hidden: bool, incremental: bool, no_cache: bool, plugins_config: PluginsConfig | None = None, performance_config: PerformanceConfig | None = None, perf_mode: bool = False) -> None:
    """Scan then analyze a project root for quick feedback."""
    logger.info("Analyzing project at %s", root)
    
    # Load plugins
    plugin_manager = PluginManager(config=plugins_config)
    plugin_manager.discover_and_load()

    scanner = ProjectScanner(
        root=root, 
        ignore_hidden=not show_hidden, 
        ignore_globs=ignore_globs,
        incremental=incremental,
        no_cache=no_cache,
        perf_mode=perf_mode,
        max_workers=performance_config.max_workers if performance_config else None,
        large_file_threshold=performance_config.large_file_threshold if performance_config else 10 * 1024 * 1024,
    )
    analyzer = ProjectAnalyzer(root=root, no_cache=no_cache, perf_mode=perf_mode)
    summary = analyzer.summarize(scanner.iter_files(), top_n=top)
    
    # Convert to dict for plugins
    summary_dict = summary.to_dict()
    
    # Run plugin hooks
    plugin_manager.hook_on_analyze(summary_dict)
    
    if as_json:
        print(json.dumps(summary_dict, indent=2))
    else:
        print(summary.describe())


def handle_ci(
    root: Path,
    as_json: bool,
    config: JupiterConfig,
    fail_on_complexity: int | None = None,
    fail_on_duplication: int | None = None,
    fail_on_unused: int | None = None,
) -> None:
    """Run scan and analysis in CI mode, checking against quality gates."""
    logger.info("Running CI analysis on %s", root)
    
    # 1. Scan
    scanner = ProjectScanner(
        root=root,
        ignore_hidden=True, # Usually CI ignores hidden files
        incremental=False, # CI usually wants a fresh scan or relies on restored cache
        no_cache=False,
        perf_mode=False,
        max_workers=config.performance.max_workers,
        large_file_threshold=config.performance.large_file_threshold,
    )
    
    # 2. Analyze
    analyzer = ProjectAnalyzer(root=root, no_cache=False, perf_mode=False)
    summary = analyzer.summarize(scanner.iter_files(), top_n=10)
    summary_dict = summary.to_dict()
    
    # 3. Check thresholds
    thresholds = config.ci.fail_on.copy()
    if fail_on_complexity is not None:
        thresholds["max_complexity"] = fail_on_complexity
    if fail_on_duplication is not None:
        thresholds["max_duplication_clusters"] = fail_on_duplication
    if fail_on_unused is not None:
        thresholds["max_unused_functions"] = fail_on_unused
        
    failures = []
    
    # Check Complexity
    max_complexity = 0
    if summary.quality and "complexity_per_file" in summary.quality:
        for item in summary.quality["complexity_per_file"]:
            if item["score"] > max_complexity:
                max_complexity = item["score"]
    
    limit_complexity = thresholds.get("max_complexity")
    if limit_complexity is not None and max_complexity > limit_complexity:
        failures.append(f"Max complexity {max_complexity} exceeds limit {limit_complexity}")

    # Check Duplication
    duplication_count = 0
    if summary.quality and "duplication_clusters" in summary.quality:
        duplication_count = len(summary.quality["duplication_clusters"])
        
    limit_duplication = thresholds.get("max_duplication_clusters")
    if limit_duplication is not None and duplication_count > limit_duplication:
        failures.append(f"Duplication clusters {duplication_count} exceeds limit {limit_duplication}")

    # Check Unused Functions
    unused_count = 0
    if summary.python_summary:
        unused_count += summary.python_summary.total_potentially_unused_functions
    
    limit_unused = thresholds.get("max_unused_functions")
    if limit_unused is not None and unused_count > limit_unused:
        failures.append(f"Unused functions {unused_count} exceeds limit {limit_unused}")

    # 4. Output
    result = {
        "status": "failed" if failures else "passed",
        "failures": failures,
        "metrics": {
            "max_complexity": max_complexity,
            "duplication_clusters": duplication_count,
            "unused_functions": unused_count,
        },
        "summary": summary_dict
    }
    
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"CI Analysis Status: {result['status'].upper()}")
        print("-" * 30)
        print(f"Max Complexity: {max_complexity} (Limit: {limit_complexity if limit_complexity else 'None'})")
        print(f"Duplication Clusters: {duplication_count} (Limit: {limit_duplication if limit_duplication else 'None'})")
        print(f"Unused Functions: {unused_count} (Limit: {limit_unused if limit_unused else 'None'})")
        
        if failures:
            print("\nFailures:")
            for f in failures:
                print(f" - {f}")
    
    if failures:
        sys.exit(1)


def handle_simulate_remove(root: Path, target: str, as_json: bool) -> None:
    # Load cache
    cache_manager = CacheManager(root)
    last_scan = cache_manager.load_last_scan()
    if not last_scan or "files" not in last_scan:
        logger.error("No scan data found. Run 'jupiter scan' first.")
        sys.exit(1)
        
    from jupiter.core.simulator import ProjectSimulator
    simulator = ProjectSimulator(last_scan["files"])
    
    if "::" in target:
        path, func = target.split("::", 1)
        result = simulator.simulate_remove_function(path, func)
    else:
        result = simulator.simulate_remove_file(target)
        
    if as_json:
        from dataclasses import asdict
        print(json.dumps(asdict(result), indent=2))
        return
        
    print(f"Simulation: {result.target}")
    print(f"Risk Score: {result.risk_score.upper()}")
    if not result.impacts:
        print("No impacts detected.")
    else:
        print(f"Impacts ({len(result.impacts)}):")
        for imp in result.impacts:
            print(f" - [{imp.severity.upper()}] {imp.target}: {imp.details} ({imp.impact_type})")


def handle_server(root: Path, host: str, port: int) -> None:
    """Start the Jupiter API server stub."""
    # Strip quotes if present (workaround for Windows cmd passing quotes)
    root = Path(str(root).strip('"\''))
    
    config = load_config(root)
    
    # CLI args override config
    final_host = host or config.server.host
    final_port = port or config.server.port
    
    install_path = Path(__file__).resolve().parent.parent.parent

    server = JupiterAPIServer(
        root=root, 
        host=final_host, 
        port=final_port,
        device_key=config.meeting.deviceKey if config.meeting.enabled else None,
        plugins_config=config.plugins,
        config=config,
        install_path=install_path
    )
    server.start()


def handle_gui(root: Path, host: str, port: int, device_key: str | None = None) -> None:
    """Lancer le serveur statique pour l'interface web."""
    # Strip quotes if present (workaround for Windows cmd passing quotes)
    root = Path(str(root).strip('"\''))
    
    logger.info("Démarrage de la GUI Jupiter sur %s:%s (racine %s)", host, port, root)
    launch_web_ui(root=root, host=host, port=port, device_key=device_key)


def handle_watch(root: Path) -> None:
    """Watch a project directory for file changes."""
    logger.info("Starting file watcher on %s...", root)
    tracked_files: dict[Path, float] = {}

    def scan_and_get_files_dict() -> dict[Path, float]:
        scanner = ProjectScanner(root=root)  # Assuming default ignore settings
        return {metadata.path: metadata.modified_timestamp for metadata in scanner.iter_files()}

    tracked_files = scan_and_get_files_dict()
    logger.info("Watching %d files for changes.", len(tracked_files))

    try:
        while True:
            time.sleep(2)
            new_files = scan_and_get_files_dict()

            # Check for new and modified files
            for path, ts in new_files.items():
                if path not in tracked_files:
                    logger.info("New file detected: %s", path)
                elif tracked_files[path] < ts:
                    logger.info("File modified: %s", path)

            # Check for deleted files
            deleted_paths = tracked_files.keys() - new_files.keys()
            for path in deleted_paths:
                logger.info("File deleted: %s", path)

            tracked_files = new_files
    except KeyboardInterrupt:
        logger.info("Stopping file watcher.")


def handle_run(root: Path, command_str: str, with_dynamic: bool) -> None:
    """Run a command with optional dynamic analysis."""
    import shlex
    from jupiter.core.runner import run_command
    
    # Split command string
    cmd_args = shlex.split(command_str)
    
    result = run_command(cmd_args, cwd=root, with_dynamic=with_dynamic)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
        
    if result.dynamic_data:
        logger.info("Dynamic analysis data captured.")
        # Merge into cache
        cache_manager = CacheManager(root)
        last_scan = cache_manager.load_last_scan()
        if last_scan:
            if "dynamic" not in last_scan or last_scan["dynamic"] is None:
                last_scan["dynamic"] = {"calls": {}, "times": {}, "call_graph": {}}
            
            if "calls" not in last_scan["dynamic"]:
                 old_calls = last_scan["dynamic"] if isinstance(last_scan["dynamic"], dict) else {}
                 last_scan["dynamic"] = {"calls": old_calls, "times": {}, "call_graph": {}}

            # Merge calls
            current_calls = last_scan["dynamic"].get("calls", {})
            new_calls = result.dynamic_data.get("calls", {})
            for func, count in new_calls.items():
                current_calls[func] = current_calls.get(func, 0) + count
            last_scan["dynamic"]["calls"] = current_calls

            # Merge times
            current_times = last_scan["dynamic"].get("times", {})
            new_times = result.dynamic_data.get("times", {})
            for func, time_val in new_times.items():
                current_times[func] = current_times.get(func, 0.0) + time_val
            last_scan["dynamic"]["times"] = current_times

            # Merge call graph
            current_graph = last_scan["dynamic"].get("call_graph", {})
            new_graph = result.dynamic_data.get("call_graph", {})
            for caller, callees in new_graph.items():
                if caller not in current_graph:
                    current_graph[caller] = {}
                for callee, count in callees.items():
                    current_graph[caller][callee] = current_graph[caller].get(callee, 0) + count
            last_scan["dynamic"]["call_graph"] = current_graph

            cache_manager.save_last_scan(last_scan)
            logger.info("Dynamic analysis results merged into cache.")


def handle_app(root: Path) -> None:
    """Start the full application (API + WebUI) and open the browser."""
    # Strip quotes if present
    root = Path(str(root).strip('"\''))
    
    config = load_config(root)
    
    # API Server settings
    api_host = config.server.host
    api_port = config.server.port
    
    # WebUI settings
    web_host = config.gui.host
    web_port = config.gui.port
    device_key = config.meeting.deviceKey if config.meeting.enabled else None
    
    install_path = Path(__file__).resolve().parent.parent.parent

    # Start API Server in a thread
    logger.info("Starting API Server on %s:%s", api_host, api_port)
    api_server = JupiterAPIServer(
        root=root, 
        host=api_host, 
        port=api_port,
        device_key=device_key,
        plugins_config=config.plugins,
        install_path=install_path
    )
    
    api_thread = threading.Thread(target=api_server.start, daemon=True)
    api_thread.start()
    
    # Wait a bit for API to start
    time.sleep(1)
    
    # Start WebUI in a thread
    logger.info("Starting Web UI on %s:%s", web_host, web_port)
    
    web_thread = threading.Thread(
        target=handle_gui, 
        args=(root, web_host, web_port, device_key), 
        daemon=True
    )
    web_thread.start()
    
    # Open browser
    url = f"http://{web_host}:{web_port}"
    logger.info("Opening browser at %s", url)
    # Give WebUI a moment to bind
    time.sleep(1)
    webbrowser.open(url)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping Jupiter App...")


def main() -> None:
    """Entrypoint for the CLI."""
    args = build_parser().parse_args()

    if args.command is None:
        default_root = resolve_root_argument(None)
        save_last_root(default_root)
        handle_app(default_root)
        return

    # Resolve the root once and reuse it (update will ignore it)
    root = resolve_root_argument(getattr(args, "root", None))
    save_last_root(root)
    config = load_config(root)
    default_backend_name = config.backends[0].name if config.backends else "local"

    if args.command == "scan":
        payload = handle_scan(
            root=root,
            show_hidden=args.show_hidden, 
            ignore_globs=args.ignore_globs,
            incremental=args.incremental,
            no_cache=args.no_cache,
            plugins_config=config.plugins,
            performance_config=config.performance,
            snapshot_label=args.snapshot_label,
            snapshot_enabled=not args.no_snapshot,
            backend_name=default_backend_name,
            perf_mode=args.perf,
        )
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
            logger.info("Wrote scan report to %s", args.output)
        else:
            print(payload)
    elif args.command == "analyze":
        handle_analyze(
            root=root,
            as_json=args.json,
            top=args.top,
            ignore_globs=args.ignore_globs,
            show_hidden=args.show_hidden,
            incremental=args.incremental,
            no_cache=args.no_cache,
            plugins_config=config.plugins,
            performance_config=config.performance,
            perf_mode=args.perf,
        )
    elif args.command == "server":
        host = args.host or config.server.host
        port = args.port or config.server.port
        handle_server(root=root, host=host, port=port)
    elif args.command == "run":
        handle_run(root=root, command_str=args.command_str, with_dynamic=args.with_dynamic)
    elif args.command == "gui":
        host = args.host or config.gui.host
        port = args.port or config.gui.port
        device_key = config.meeting.deviceKey if config.meeting.enabled else None
        handle_gui(root=root, host=host, port=port, device_key=device_key)
    elif args.command == "watch":
        handle_watch(root)
    elif args.command == "snapshots":
        snap_root = resolve_root_argument(getattr(args, "root", None))
        save_last_root(snap_root)
        if args.snapshot_command == "list":
            handle_snapshot_list(snap_root, args.json)
        elif args.snapshot_command == "show":
            handle_snapshot_show(snap_root, args.snapshot_id, args.report, args.json)
        elif args.snapshot_command == "diff":
            handle_snapshot_diff(snap_root, args.snapshot_a, args.snapshot_b, args.json)
        else:
            raise ValueError(f"Unhandled snapshot command {args.snapshot_command}")
    elif args.command == "simulate":
        sim_root = resolve_root_argument(getattr(args, "root", None))
        save_last_root(sim_root)
        if args.simulate_command == "remove":
            handle_simulate_remove(sim_root, args.target, args.json)
    elif args.command == "update":
        handle_update(args.source, args.force)
    elif args.command == "ci":
        handle_ci(
            root=root,
            as_json=args.json,
            config=config,
            fail_on_complexity=args.fail_on_complexity,
            fail_on_duplication=args.fail_on_duplication,
            fail_on_unused=args.fail_on_unused,
        )
    else:
        raise ValueError(f"Unhandled command {args.command}")


if __name__ == "__main__":
    main()