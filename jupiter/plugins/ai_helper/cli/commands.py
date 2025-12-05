"""
cli/commands.py – CLI commands for AI Helper plugin.
Version: 1.1.0

Uses argparse to remain lightweight; compatible with Typer if adopted.
Conforme à plugins_architecture.md v0.4.0

@module jupiter.plugins.ai_helper.cli.commands
"""

import argparse
import json
import sys
from typing import Optional


def build_parser(subparsers):
    """
    Add plugin subcommands to the main CLI parser.
    
    Args:
        subparsers: argparse subparsers object.
    """
    parser = subparsers.add_parser(
        "ai",
        help="AI Helper commands - AI-assisted code analysis"
    )
    sub = parser.add_subparsers(dest="ai_cmd")

    # Subcommand: suggest
    suggest_parser = sub.add_parser(
        "suggest",
        help="Generate AI suggestions for the project"
    )
    suggest_parser.add_argument(
        "--type", "-t",
        choices=["refactoring", "doc", "security", "optimization", "testing", "cleanup", "all"],
        default="all",
        help="Type of suggestions to generate"
    )
    suggest_parser.add_argument(
        "--severity", "-s",
        choices=["info", "low", "medium", "high", "critical"],
        default="info",
        help="Minimum severity level"
    )
    suggest_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    suggest_parser.set_defaults(func=cmd_suggest)

    # Subcommand: analyze-file
    analyze_parser = sub.add_parser(
        "analyze-file",
        help="Analyze a specific file with AI"
    )
    analyze_parser.add_argument(
        "file",
        help="Path to the file to analyze"
    )
    analyze_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    analyze_parser.set_defaults(func=cmd_analyze_file)

    # Subcommand: status
    status_parser = sub.add_parser(
        "status",
        help="Show AI Helper status and configuration"
    )
    status_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    status_parser.set_defaults(func=cmd_status)

    # Subcommand: config
    config_parser = sub.add_parser(
        "config",
        help="Manage AI Helper configuration"
    )
    config_sub = config_parser.add_subparsers(dest="config_cmd")
    
    # config show
    config_show = config_sub.add_parser("show", help="Show current configuration")
    config_show.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    config_show.set_defaults(func=cmd_config_show)
    
    # config set
    config_set = config_sub.add_parser("set", help="Set configuration value")
    config_set.add_argument("key", help="Configuration key (e.g., provider, enabled)")
    config_set.add_argument("value", help="Configuration value")
    config_set.set_defaults(func=cmd_config_set)
    
    # config reset
    config_reset = config_sub.add_parser("reset", help="Reset configuration to defaults")
    config_reset.set_defaults(func=cmd_config_reset)

    # Subcommand: health
    health_parser = sub.add_parser(
        "health",
        help="Check plugin health status"
    )
    health_parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output as JSON"
    )
    health_parser.set_defaults(func=cmd_health)


def cmd_suggest(args):
    """
    Generate AI suggestions for the project.
    """
    try:
        from jupiter.plugins import ai_helper
        from jupiter.core import ProjectScanner, ProjectAnalyzer, ScanReport
        from jupiter.core.state import load_last_root
        from pathlib import Path
        
        # Run scan and analyze to get data
        print("[AI Helper] Running project analysis...")
        root = load_last_root() or Path.cwd()
        scanner = ProjectScanner(root)
        scan_report = ScanReport.from_files(root=root, files=scanner.iter_files())
        
        # Convert to dict format for hook
        report_dict = scan_report.to_dict()
        ai_helper.on_scan(report_dict)
        
        analyzer = ProjectAnalyzer(root=root)
        summary_obj = analyzer.summarize(scan_report.files)
        summary = summary_obj.to_dict() if hasattr(summary_obj, 'to_dict') else vars(summary_obj)
        ai_helper.on_analyze(summary)
        
        suggestions = ai_helper.get_suggestions()
        
        # Filter by type if specified
        if args.type != "all":
            suggestions = [s for s in suggestions if s.get("type") == args.type]
        
        # Filter by severity
        severity_order = ["info", "low", "medium", "high", "critical"]
        threshold_idx = severity_order.index(args.severity)
        suggestions = [
            s for s in suggestions 
            if severity_order.index(s.get("severity", "info")) >= threshold_idx
        ]
        
        if args.json:
            print(json.dumps(suggestions, indent=2))
        else:
            if not suggestions:
                print("[AI Helper] No suggestions generated.")
            else:
                print(f"\n[AI Helper] Generated {len(suggestions)} suggestion(s):\n")
                for i, s in enumerate(suggestions, 1):
                    severity = s.get("severity", "info").upper()
                    stype = s.get("type", "unknown")
                    path = s.get("path", "Unknown")
                    details = s.get("details", "")
                    print(f"  {i}. [{severity}] [{stype}] {path}")
                    print(f"     {details}\n")
                    
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_analyze_file(args):
    """
    Analyze a specific file with AI.
    """
    try:
        from jupiter.plugins import ai_helper
        from jupiter.plugins.ai_helper.core.logic import analyze_single_file
        
        config = ai_helper.get_config()
        result = analyze_single_file(args.file, config)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n[AI Helper] Analysis of {args.file}:\n")
            suggestions = result.get("suggestions", [])
            if not suggestions:
                print("  No suggestions for this file.")
            else:
                for i, s in enumerate(suggestions, 1):
                    severity = s.get("severity", "info").upper()
                    stype = s.get("type", "unknown")
                    details = s.get("details", "")
                    print(f"  {i}. [{severity}] [{stype}] {details}")
                    
    except FileNotFoundError:
        print(f"[AI Helper] Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """
    Show AI Helper status and configuration.
    """
    try:
        from jupiter.plugins import ai_helper
        
        health = ai_helper.health()
        metrics = ai_helper.metrics()
        config = ai_helper.get_config()
        
        if args.json:
            result = {
                "health": health,
                "metrics": metrics,
                "config": config
            }
            print(json.dumps(result, indent=2))
        else:
            print("\n[AI Helper] Status:\n")
            print(f"  Health: {health.get('status', 'unknown')}")
            print(f"  Message: {health.get('message', '-')}")
            print(f"  Provider: {config.get('provider', 'mock')}")
            print(f"  Enabled: {config.get('enabled', False)}")
            print(f"\n  Executions: {metrics.get('ai_helper_executions_total', 0)}")
            print(f"  Total Suggestions: {metrics.get('ai_helper_suggestions_total', 0)}")
            print(f"  Last Run: {metrics.get('ai_helper_last_execution', '-')}")
            
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_health(args):
    """
    Check plugin health status.
    """
    try:
        from jupiter.plugins import ai_helper
        
        health = ai_helper.health()
        
        if args.json:
            print(json.dumps(health, indent=2))
        else:
            status = health.get("status", "unknown")
            message = health.get("message", "-")
            details = health.get("details", {})
            
            icon = "✓" if status == "healthy" else "⚠"
            print(f"\n[AI Helper] Health: {icon} {status.upper()}")
            print(f"  Message: {message}")
            if details:
                print("  Details:")
                for k, v in details.items():
                    print(f"    {k}: {v}")
                    
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config_show(args):
    """
    Show current configuration.
    """
    try:
        from jupiter.plugins import ai_helper
        
        config = ai_helper.get_config()
        
        if args.json:
            print(json.dumps(config, indent=2))
        else:
            print("\n[AI Helper] Configuration:\n")
            for k, v in sorted(config.items()):
                # Mask API key
                if "key" in k.lower() and v:
                    v = "***" + str(v)[-4:] if len(str(v)) > 4 else "****"
                print(f"  {k}: {v}")
                
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config_set(args):
    """
    Set a configuration value.
    """
    try:
        from jupiter.plugins import ai_helper
        
        config = ai_helper.get_config()
        
        # Parse value
        value = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)
        
        config[args.key] = value
        ai_helper.configure(config)
        
        print(f"[AI Helper] Set {args.key} = {value}")
        
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_config_reset(args):
    """
    Reset configuration to defaults.
    """
    try:
        from jupiter.plugins import ai_helper
        
        result = ai_helper.reset_settings()
        
        if result.get("success"):
            print("[AI Helper] Configuration reset to defaults.")
        else:
            print(f"[AI Helper] Failed to reset: {result.get('message', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"[AI Helper] Error: {e}", file=sys.stderr)
        sys.exit(1)


def register_cli_contribution(main_subparsers):
    """
    Entry point called by Bridge to register CLI commands.
    
    Args:
        main_subparsers: Subparsers from the main CLI.
    """
    build_parser(main_subparsers)
