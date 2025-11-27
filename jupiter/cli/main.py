"""Command line entrypoint for Jupiter."""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from jupiter.config import load_config
from jupiter.core import ProjectAnalyzer, ProjectScanner, ScanReport
from jupiter.server import JupiterAPIServer
from jupiter.web import launch_web_ui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Jupiter project inspection tool")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan_parser = subcommands.add_parser("scan", help="Scan a project directory")
    scan_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Root folder to scan")
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

    analyze_parser = subcommands.add_parser("analyze", help="Analyze a project directory")
    analyze_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Root folder to analyze")
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

    server_parser = subcommands.add_parser("server", help="Start the API server")
    server_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Project root to serve")
    server_parser.add_argument("--host", help="Host to bind")
    server_parser.add_argument("--port", type=int, help="Port to bind")

    gui_parser = subcommands.add_parser("gui", help="Lancer l'interface web locale")
    gui_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Projet à afficher dans la GUI")
    gui_parser.add_argument("--host", help="Hôte HTTP pour la GUI")
    gui_parser.add_argument("--port", type=int, help="Port HTTP pour la GUI")

    watch_parser = subcommands.add_parser("watch", help="Watch a project directory for changes")
    watch_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Root folder to watch")

    return parser


def handle_scan(root: Path, show_hidden: bool, ignore_globs: list[str] | None) -> str:
    """Run a filesystem scan and return a JSON report."""
    logger.info("Scanning project at %s", root)
    scanner = ProjectScanner(root=root, ignore_hidden=not show_hidden, ignore_globs=ignore_globs)
    report = ScanReport.from_files(root=root, files=scanner.iter_files())
    payload = json.dumps(report.to_dict(), indent=2)
    return payload


def handle_analyze(root: Path, as_json: bool, top: int, ignore_globs: list[str] | None, show_hidden: bool) -> None:
    """Scan then analyze a project root for quick feedback."""
    logger.info("Analyzing project at %s", root)
    scanner = ProjectScanner(root=root, ignore_hidden=not show_hidden, ignore_globs=ignore_globs)
    analyzer = ProjectAnalyzer(root=root)
    summary = analyzer.summarize(scanner.iter_files(), top_n=top)
    if as_json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(summary.describe())


def handle_server(root: Path, host: str, port: int) -> None:
    """Start the Jupiter API server stub."""
    server = JupiterAPIServer(root=root, host=host, port=port)
    server.start()


def handle_gui(root: Path, host: str, port: int) -> None:
    """Lancer le serveur statique pour l'interface web."""
    logger.info("Démarrage de la GUI Jupiter sur %s:%s (racine %s)", host, port, root)
    launch_web_ui(root=root, host=host, port=port)


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


def main() -> None:
    """Entrypoint for the CLI."""
    args = build_parser().parse_args()
    config = load_config(args.root)

    if args.command == "scan":
        payload = handle_scan(root=args.root, show_hidden=args.show_hidden, ignore_globs=args.ignore_globs)
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
            logger.info("Wrote scan report to %s", args.output)
        else:
            print(payload)
    elif args.command == "analyze":
        handle_analyze(
            root=args.root,
            as_json=args.json,
            top=args.top,
            ignore_globs=args.ignore_globs,
            show_hidden=args.show_hidden,
        )
    elif args.command == "server":
        host = args.host or config.server.host
        port = args.port or config.server.port
        handle_server(root=args.root, host=host, port=port)
    elif args.command == "gui":
        host = args.host or config.gui.host
        port = args.port or config.gui.port
        handle_gui(root=args.root, host=host, port=port)
    elif args.command == "watch":
        handle_watch(args.root)
    else:
        raise ValueError(f"Unhandled command {args.command}")


if __name__ == "__main__":
    main()