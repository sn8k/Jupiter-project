"""
Command line entrypoint for Jupiter.

Version: 1.1.1
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any

from jupiter import __version__
from jupiter.config import load_config
from jupiter.core.logging_utils import configure_logging
from jupiter.core.state import save_last_root
from jupiter.cli.utils import resolve_root_argument
from jupiter.cli.command_handlers import (
    handle_update,
    handle_scan,
    handle_analyze,
    handle_ci,
    handle_server,
    handle_gui,
    handle_watch,
    handle_run,
    handle_app,
    handle_snapshot_list,
    handle_snapshot_show,
    handle_snapshot_diff,
    handle_simulate_remove,
    handle_meeting_check_license,
    handle_autodiag,
)

configure_logging("INFO")
logger = logging.getLogger(__name__)


# =============================================================================
# CLI HANDLER REGISTRY (Phase 2 - for autodiag introspection)
# =============================================================================

# Map of command names to their handler functions
CLI_HANDLERS: Dict[str, Any] = {
    "scan": handle_scan,
    "analyze": handle_analyze,
    "ci": handle_ci,
    "server": handle_server,
    "gui": handle_gui,
    "watch": handle_watch,
    "run": handle_run,
    "app": handle_app,
    "update": handle_update,
    "snapshots_list": handle_snapshot_list,
    "snapshots_show": handle_snapshot_show,
    "snapshots_diff": handle_snapshot_diff,
    "simulate_remove": handle_simulate_remove,
    "meeting_check_license": handle_meeting_check_license,
    "autodiag": handle_autodiag,
}


def get_cli_handlers() -> List[Dict[str, Any]]:
    """
    Get list of all CLI handlers for autodiag introspection.
    
    Returns:
        List of handler info dicts with:
        - command: Command name
        - function_name: Handler function name
        - module: Module path
        - qualname: Qualified name
    """
    handlers = []
    for command, func in CLI_HANDLERS.items():
        handlers.append({
            "command": command,
            "function_name": getattr(func, "__name__", str(func)),
            "module": getattr(func, "__module__", "unknown"),
            "qualname": getattr(func, "__qualname__", getattr(func, "__name__", str(func))),
        })
    return handlers


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Jupiter project inspection tool")
    parser.add_argument("--version", action="version", version=f"jupiter {__version__}")
    parser.add_argument("--root", type=Path, default=None, help="Project root (optional, overrides current directory)")
    
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
    scan_parser.add_argument("--no-snapshot", action="store_true", help="Skip automatic snapshot creation")
    scan_parser.add_argument("--snapshot-label", help="Override the generated snapshot label")
    scan_parser.add_argument("--perf", action="store_true", help="Enable performance profiling")

    analyze_parser = subcommands.add_parser("analyze", help="Analyze a project directory")
    analyze_parser.add_argument("root", type=Path, nargs="?", default=None, help="Root folder to analyze")
    analyze_parser.add_argument("--json", action="store_true", help="Emit the summary as JSON")
    analyze_parser.add_argument("--perf", action="store_true", help="Enable performance profiling")
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
    run_parser.add_argument("command_str", help="Command to run (e.g. python script.py)")
    run_parser.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    run_parser.add_argument("--with-dynamic", action="store_true", help="Enable dynamic analysis")

    gui_parser = subcommands.add_parser("gui", help="Lancer l interface web locale")
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

    snap_show = snapshots_sub.add_parser("show", help="Show a snapshot metadata or report")
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

    # Meeting subcommand
    meeting_parser = subcommands.add_parser("meeting", help="Meeting service integration commands")
    meeting_sub = meeting_parser.add_subparsers(dest="meeting_command", required=True)
    
    meeting_check = meeting_sub.add_parser("check-license", help="Check Jupiter license via Meeting API")
    meeting_check.add_argument("root", type=Path, nargs="?", default=None, help="Project root")
    meeting_check.add_argument("--json", action="store_true", help="Output as JSON")

    # Autodiag subcommand (Phase 4)
    autodiag_parser = subcommands.add_parser("autodiag", help="Run autodiagnostic to validate unused function detection")
    autodiag_parser.add_argument("root", type=Path, nargs="?", default=None, help="Project root to analyze")
    autodiag_parser.add_argument("--json", action="store_true", help="Output as JSON")
    autodiag_parser.add_argument("--api-url", help="Main API base URL (default: http://localhost:8000)")
    autodiag_parser.add_argument("--diag-url", help="Diag API base URL (default: http://127.0.0.1:8081)")
    autodiag_parser.add_argument("--skip-cli", action="store_true", help="Skip CLI scenario tests")
    autodiag_parser.add_argument("--skip-api", action="store_true", help="Skip API scenario tests")
    autodiag_parser.add_argument("--skip-plugins", action="store_true", help="Skip plugin hook tests")
    autodiag_parser.add_argument("--timeout", type=float, default=30.0, help="Timeout per scenario (seconds)")

    return parser
def main() -> None:
    """Entrypoint for the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        default_root = resolve_root_argument(None)
        save_last_root(default_root)
        handle_app(default_root)
        return

    # Resolve the root once and reuse it (update will ignore it)
    root = resolve_root_argument(getattr(args, "root", None))
    save_last_root(root)
    config = load_config(root)
    active_level = configure_logging(
        config.logging.level,
        log_file=config.logging.path,
        reset_on_start=config.logging.reset_on_start,
    )
    logger.info("Log level set to %s", active_level)

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
        device_key = config.meeting.deviceKey
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
    elif args.command == "meeting":
        meeting_root = resolve_root_argument(getattr(args, "root", None))
        save_last_root(meeting_root)
        if args.meeting_command == "check-license":
            exit_code = handle_meeting_check_license(meeting_root, args.json)
            raise SystemExit(exit_code)
        else:
            raise ValueError(f"Unhandled meeting command {args.meeting_command}")
    elif args.command == "autodiag":
        autodiag_root = resolve_root_argument(getattr(args, "root", None))
        save_last_root(autodiag_root)
        exit_code = handle_autodiag(
            root=autodiag_root,
            as_json=args.json,
            api_url=args.api_url,
            diag_url=args.diag_url,
            skip_cli=args.skip_cli,
            skip_api=args.skip_api,
            skip_plugins=args.skip_plugins,
            timeout=args.timeout,
        )
        raise SystemExit(exit_code)
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