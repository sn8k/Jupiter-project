"""Command line entrypoint for Jupiter."""

from __future__ import annotations

import argparse
import json
import logging
import time
import sys
import threading
import webbrowser
from pathlib import Path

from jupiter import __version__
from jupiter.config import load_config, PluginsConfig
from jupiter.core import ProjectAnalyzer, ProjectScanner, ScanReport
from jupiter.core.cache import CacheManager
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

    analyze_parser = subcommands.add_parser("analyze", help="Analyze a project directory")
    analyze_parser.add_argument("root", type=Path, nargs="?", default=None, help="Root folder to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="Emit the summary as JSON")
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

    return parser


def handle_scan(root: Path, show_hidden: bool, ignore_globs: list[str] | None, incremental: bool, no_cache: bool, plugins_config: PluginsConfig | None = None) -> str:
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
        no_cache=no_cache
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
    
    payload = json.dumps(report_dict, indent=2)
    return payload


def handle_analyze(root: Path, as_json: bool, top: int, ignore_globs: list[str] | None, show_hidden: bool, incremental: bool, no_cache: bool, plugins_config: PluginsConfig | None = None) -> None:
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
        no_cache=no_cache
    )
    analyzer = ProjectAnalyzer(root=root, no_cache=no_cache)
    summary = analyzer.summarize(scanner.iter_files(), top_n=top)
    
    # Convert to dict for plugins
    summary_dict = summary.to_dict()
    
    # Run plugin hooks
    plugin_manager.hook_on_analyze(summary_dict)
    
    if as_json:
        print(json.dumps(summary_dict, indent=2))
    else:
        print(summary.describe())


def handle_server(root: Path, host: str, port: int) -> None:
    """Start the Jupiter API server stub."""
    # Strip quotes if present (workaround for Windows cmd passing quotes)
    root = Path(str(root).strip('"\''))
    
    config = load_config(root)
    
    # CLI args override config
    final_host = host or config.server.host
    final_port = port or config.server.port
    
    server = JupiterAPIServer(
        root=root, 
        host=final_host, 
        port=final_port,
        device_key=config.meeting.deviceKey if config.meeting.enabled else None,
        plugins_config=config.plugins
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
    
    # Start API Server in a thread
    logger.info("Starting API Server on %s:%s", api_host, api_port)
    api_server = JupiterAPIServer(
        root=root, 
        host=api_host, 
        port=api_port,
        device_key=device_key,
        plugins_config=config.plugins
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

    if args.command == "scan":
        payload = handle_scan(
            root=root,
            show_hidden=args.show_hidden, 
            ignore_globs=args.ignore_globs,
            incremental=args.incremental,
            no_cache=args.no_cache,
            plugins_config=config.plugins
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
            plugins_config=config.plugins
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
    elif args.command == "update":
        handle_update(args.source, args.force)
    else:
        raise ValueError(f"Unhandled command {args.command}")


if __name__ == "__main__":
    main()