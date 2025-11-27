"""Command line entrypoint for Jupiter."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from jupiter.core import ProjectAnalyzer, ProjectScanner, ScanReport
from jupiter.server import JupiterAPIServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(description="Jupiter project inspection tool")
    subcommands = parser.add_subparsers(dest="command", required=True)

    scan_parser = subcommands.add_parser("scan", help="Scan a project directory")
    scan_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Root folder to scan")
    scan_parser.add_argument("--show-hidden", action="store_true", help="Include hidden files")

    analyze_parser = subcommands.add_parser("analyze", help="Analyze a project directory")
    analyze_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Root folder to analyze")

    server_parser = subcommands.add_parser("server", help="Start the API server")
    server_parser.add_argument("root", type=Path, nargs="?", default=Path.cwd(), help="Project root to serve")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind")

    return parser


def handle_scan(root: Path, show_hidden: bool) -> None:
    """Run a filesystem scan and emit JSON report."""

    logger.info("Scanning project at %s", root)
    scanner = ProjectScanner(root=root, ignore_hidden=not show_hidden)
    report = ScanReport.from_files(root=root, files=scanner.iter_files())
    print(json.dumps(report.to_dict(), indent=2))


def handle_analyze(root: Path) -> None:
    """Scan then analyze a project root for quick feedback."""

    logger.info("Analyzing project at %s", root)
    scanner = ProjectScanner(root=root)
    analyzer = ProjectAnalyzer(root=root)
    summary = analyzer.summarize(scanner.iter_files())
    print(summary.describe())


def handle_server(root: Path, host: str, port: int) -> None:
    """Start the Jupiter API server stub."""

    server = JupiterAPIServer(root=root, host=host, port=port)
    server.start()


def main() -> None:
    """Entrypoint for the CLI."""

    args = build_parser().parse_args()

    if args.command == "scan":
        handle_scan(root=args.root, show_hidden=args.show_hidden)
    elif args.command == "analyze":
        handle_analyze(root=args.root)
    elif args.command == "server":
        handle_server(root=args.root, host=args.host, port=args.port)
    else:
        raise ValueError(f"Unhandled command {args.command}")


if __name__ == "__main__":
    main()
