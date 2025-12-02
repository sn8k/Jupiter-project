import json
import logging
import time
import sys
import threading
import webbrowser
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jupiter.config import load_config, load_merged_config, PluginsConfig, PerformanceConfig, JupiterConfig
from jupiter.core import ProjectAnalyzer, ProjectScanner, ScanReport
from jupiter.core.cache import CacheManager
from jupiter.core.history import HistoryManager
from jupiter.core.plugin_manager import PluginManager
from jupiter.core.state import save_last_root
from jupiter.core.updater import apply_update
from jupiter.server import JupiterAPIServer
from jupiter.web import launch_web_ui
from jupiter.core.runner import run_command
from jupiter.core.simulator import ProjectSimulator

logger = logging.getLogger(__name__)

@dataclass
class ScanOptions:
    """Options used to configure scan/analyze workflows."""

    root: Path
    show_hidden: bool
    ignore_globs: list[str] | None
    incremental: bool
    no_cache: bool
    plugins_config: PluginsConfig | None
    performance_config: PerformanceConfig | None
    perf_mode: bool


@dataclass
class SnapshotOptions:
    """Controls snapshot persistence to keep CLI flow predictable."""

    enabled: bool = True
    label: str | None = None
    backend_name: str | None = None


@dataclass
class WorkflowServices:
    """Shared services so scan/analyze handlers reuse the same setup."""

    options: ScanOptions
    plugin_manager: PluginManager
    scanner: ProjectScanner
    cache_manager: CacheManager


def _build_scan_options(
    root: Path,
    show_hidden: bool,
    ignore_globs: list[str] | None,
    incremental: bool,
    no_cache: bool,
    plugins_config: PluginsConfig | None,
    performance_config: PerformanceConfig | None,
    perf_mode: bool,
) -> ScanOptions:
    """Collect scan options so callers only need two lines."""
    return ScanOptions(
        root=root,
        show_hidden=show_hidden,
        ignore_globs=ignore_globs,
        incremental=incremental,
        no_cache=no_cache,
        plugins_config=plugins_config,
        performance_config=performance_config,
        perf_mode=perf_mode,
    )


def _init_workflow_services(options: ScanOptions) -> WorkflowServices:
    """Create plugin/scanner/cache services once per command."""
    plugin_manager = PluginManager(config=options.plugins_config)
    plugin_manager.discover_and_load()
    scanner = ProjectScanner(
        root=options.root,
        ignore_hidden=not options.show_hidden,
        ignore_globs=options.ignore_globs,
        incremental=options.incremental,
        no_cache=options.no_cache,
        perf_mode=options.perf_mode,
        max_workers=options.performance_config.max_workers if options.performance_config else None,
        large_file_threshold=options.performance_config.large_file_threshold if options.performance_config else 10 * 1024 * 1024,
    )
    cache_manager = CacheManager(options.root)
    return WorkflowServices(
        options=options,
        plugin_manager=plugin_manager,
        scanner=scanner,
        cache_manager=cache_manager,
    )


def _collect_scan_payload(services: WorkflowServices) -> dict[str, Any]:
    """Run the scan and enrich payload with plugin metadata."""
    report = ScanReport.from_files(root=services.options.root, files=services.scanner.iter_files())
    report_dict = report.to_dict()
    report_dict["plugins"] = services.plugin_manager.get_plugins_info()
    report_dict["project_path"] = str(services.options.root)
    services.plugin_manager.hook_on_scan(report_dict, project_root=services.options.root)
    return report_dict


def _persist_scan_artifacts(
    services: WorkflowServices,
    report_dict: dict[str, Any],
    snapshot_options: SnapshotOptions,
) -> None:
    """Persist cache and snapshots with consistent error handling."""
    services.cache_manager.save_last_scan(report_dict)
    if not snapshot_options.enabled:
        return

    try:
        history = HistoryManager(services.options.root)
        metadata = history.create_snapshot(
            report_dict,
            label=snapshot_options.label,
            backend_name=snapshot_options.backend_name,
        )
        logger.info("Snapshot saved as %s", metadata.id)
    except Exception as exc:  # pragma: no cover - just log and continue
        logger.warning("Failed to store snapshot: %s", exc)


def _build_analyzer(options: ScanOptions) -> ProjectAnalyzer:
    """Factory kept separate so tests can stub it easily."""
    return ProjectAnalyzer(root=options.root, no_cache=options.no_cache, perf_mode=options.perf_mode)


def _build_services_from_args(
    root: Path,
    show_hidden: bool,
    ignore_globs: list[str] | None,
    incremental: bool,
    no_cache: bool,
    plugins_config: PluginsConfig | None,
    performance_config: PerformanceConfig | None,
    perf_mode: bool,
) -> tuple[ScanOptions, WorkflowServices]:
    """Create scan options and services from CLI-style arguments."""
    scan_options = _build_scan_options(
        root=root,
        show_hidden=show_hidden,
        ignore_globs=ignore_globs,
        incremental=incremental,
        no_cache=no_cache,
        plugins_config=plugins_config,
        performance_config=performance_config,
        perf_mode=perf_mode,
    )
    services = _init_workflow_services(scan_options)
    return scan_options, services


def _evaluate_ci_thresholds(summary, thresholds: dict[str, int | None]) -> tuple[list[str], dict[str, int]]:
    """Compute CI failures and metrics deltas in one place."""
    failures: list[str] = []

    max_complexity = 0
    if summary.quality and "complexity_per_file" in summary.quality:
        for item in summary.quality["complexity_per_file"]:
            if item["score"] > max_complexity:
                max_complexity = item["score"]

    duplication_count = 0
    if summary.quality and "duplication_clusters" in summary.quality:
        duplication_count = len(summary.quality["duplication_clusters"])

    unused_count = summary.python_summary.total_potentially_unused_functions if summary.python_summary else 0

    limit_complexity = thresholds.get("max_complexity")
    if limit_complexity is not None and max_complexity > limit_complexity:
        failures.append(f"Max complexity {max_complexity} exceeds limit {limit_complexity}")

    limit_duplication = thresholds.get("max_duplication_clusters")
    if limit_duplication is not None and duplication_count > limit_duplication:
        failures.append(f"Duplication clusters {duplication_count} exceeds limit {limit_duplication}")

    limit_unused = thresholds.get("max_unused_functions")
    if limit_unused is not None and unused_count > limit_unused:
        failures.append(f"Unused functions {unused_count} exceeds limit {limit_unused}")

    metrics = {
        "max_complexity": max_complexity,
        "duplication_clusters": duplication_count,
        "unused_functions": unused_count,
    }
    return failures, metrics

def handle_update(source: str, force: bool = False) -> None:
    """Handle self-update."""
    try:
        apply_update(source, force)
    except Exception as e:
        logger.error("Update failed: %s", e)
        if not force:
            return

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
    
    scan_options, services = _build_services_from_args(
        root=root,
        show_hidden=show_hidden,
        ignore_globs=ignore_globs,
        incremental=incremental,
        no_cache=no_cache,
        plugins_config=plugins_config,
        performance_config=performance_config,
        perf_mode=perf_mode,
    )
    report_dict = _collect_scan_payload(services)
    snapshot_options = SnapshotOptions(
        enabled=snapshot_enabled,
        label=snapshot_label,
        backend_name=backend_name,
    )
    _persist_scan_artifacts(services, report_dict, snapshot_options)
    return json.dumps(report_dict, indent=2)


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
    
    scan_options, services = _build_services_from_args(
        root=root,
        show_hidden=show_hidden,
        ignore_globs=ignore_globs,
        incremental=incremental,
        no_cache=no_cache,
        plugins_config=plugins_config,
        performance_config=performance_config,
        perf_mode=perf_mode,
    )
    analyzer = _build_analyzer(scan_options)
    summary = analyzer.summarize(services.scanner.iter_files(), top_n=top)
    summary_dict = summary.to_dict()
    services.plugin_manager.hook_on_analyze(summary_dict, project_root=root)
    
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
    
    # 1. Scan + analyze via shared helpers to keep behavior consistent with CLI commands
    scan_options = _build_scan_options(
        root=root,
        show_hidden=False,
        ignore_globs=None,
        incremental=False,
        no_cache=False,
        plugins_config=config.plugins,
        performance_config=config.performance,
        perf_mode=False,
    )
    services = _init_workflow_services(scan_options)
    analyzer = _build_analyzer(scan_options)
    summary = analyzer.summarize(services.scanner.iter_files(), top_n=10)
    summary_dict = summary.to_dict()
    services.plugin_manager.hook_on_analyze(summary_dict, project_root=root)
    
    # 3. Check thresholds
    thresholds: dict[str, int | None] = config.ci.fail_on.copy()
    if fail_on_complexity is not None:
        thresholds["max_complexity"] = fail_on_complexity
    if fail_on_duplication is not None:
        thresholds["max_duplication_clusters"] = fail_on_duplication
    if fail_on_unused is not None:
        thresholds["max_unused_functions"] = fail_on_unused
        
    failures, metrics = _evaluate_ci_thresholds(summary, thresholds)

    # 4. Output
    result = {
        "status": "failed" if failures else "passed",
        "failures": failures,
        "metrics": metrics,
        "summary": summary_dict,
    }
    
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"CI Analysis Status: {result['status'].upper()}")
        print("-" * 30)
        print(f"Max Complexity: {metrics['max_complexity']} (Limit: {thresholds.get('max_complexity') or 'None'})")
        print(f"Duplication Clusters: {metrics['duplication_clusters']} (Limit: {thresholds.get('max_duplication_clusters') or 'None'})")
        print(f"Unused Functions: {metrics['unused_functions']} (Limit: {thresholds.get('max_unused_functions') or 'None'})")
        
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
    
    install_path = Path(__file__).resolve().parent.parent.parent
    # Use merged config to get global settings (Meeting, Server) combined with project settings
    config = load_merged_config(install_path, root)
    
    # CLI args override config
    final_host = host or config.server.host
    final_port = port or config.server.port

    server = JupiterAPIServer(
        root=root, 
        host=final_host, 
        port=final_port,
        device_key=config.meeting.deviceKey,
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
    
    # Split command string
    # On Windows, shlex.split consumes backslashes. Use posix=False or manual split if needed.
    # Ideally, we should respect the shell quoting.
    if sys.platform == "win32":
        cmd_args = shlex.split(command_str, posix=False)
    else:
        cmd_args = shlex.split(command_str)
    
    result = run_command(cmd_args, cwd=root, with_dynamic=with_dynamic)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
        
    if result.dynamic_data:
        logger.info("Dynamic analysis data captured.")
        cache_manager = CacheManager(root)
        cache_manager.merge_dynamic_data(result.dynamic_data)
        logger.info("Dynamic analysis results merged into cache.")


def handle_app(root: Path) -> None:
    """Start the full application (API + WebUI) and open the browser."""
    # Strip quotes if present
    root = Path(str(root).strip('"\''))
    
    install_path = Path(__file__).resolve().parent.parent.parent
    
    # Try to load merged config to get global settings (Meeting, Server, GUI)
    try:
        config = load_merged_config(install_path, root)
        api_host = config.server.host
        api_port = config.server.port
        web_host = config.gui.host
        web_port = config.gui.port
        device_key = config.meeting.deviceKey
        plugins_config = config.plugins
    except Exception:
        # Fallback defaults for setup mode
        api_host = "127.0.0.1"
        api_port = 8000
        web_host = "127.0.0.1"
        web_port = 8050
        device_key = None
        plugins_config = None
        config = None

    # Start API Server in a thread
    logger.info("Starting API Server on %s:%s", api_host, api_port)

    api_server = JupiterAPIServer(
        root=root, 
        host=api_host, 
        port=api_port,
        device_key=device_key,
        plugins_config=config.plugins if config else plugins_config,
        config=config,
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


def handle_meeting_check_license(root: Path, as_json: bool) -> int:
    """Check the Jupiter Meeting license and display the result.
    
    Args:
        root: The project root path.
        as_json: Whether to output as JSON.
    
    Returns:
        Exit code: 0 = valid, 1 = invalid, 2 = config_error, 3 = network_error.
    """
    from jupiter.server.meeting_adapter import MeetingAdapter, MeetingLicenseStatus
    
    config = load_config(root)
    meeting_config = config.meeting
    
    # Check if device_key is configured
    device_key = meeting_config.deviceKey
    if not device_key:
        result = {
            "status": "config_error",
            "message": "No device_key configured in Meeting settings.",
            "device_key": None,
            "meeting_base_url": meeting_config.base_url,
            "device_type_expected": meeting_config.device_type,
        }
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print("❌ License Check Failed: Configuration Error")
            print(f"   Message: {result['message']}")
            print(f"   Meeting API: {result['meeting_base_url']}")
        return 2
    
    # Create adapter and check license
    adapter = MeetingAdapter(
        device_key=device_key,
        project_root=root,
        base_url=meeting_config.base_url,
        device_type_expected=meeting_config.device_type,
        timeout_seconds=meeting_config.timeout_seconds,
        auth_token=meeting_config.auth_token,
    )
    
    license_result = adapter.get_license_status()
    result_dict = license_result.to_dict()
    
    if as_json:
        print(json.dumps(result_dict, indent=2))
    else:
        status = license_result.status
        if status == MeetingLicenseStatus.VALID:
            print("✅ License Check: VALID")
        elif status == MeetingLicenseStatus.INVALID:
            print("❌ License Check: INVALID")
        elif status == MeetingLicenseStatus.NETWORK_ERROR:
            print("⚠️  License Check: NETWORK ERROR")
        elif status == MeetingLicenseStatus.CONFIG_ERROR:
            print("❌ License Check: CONFIGURATION ERROR")
        else:
            print(f"❓ License Check: {status.value.upper()}")
        
        print(f"   Message: {license_result.message}")
        print(f"   Device Key: {license_result.device_key}")
        print(f"   Meeting API: {license_result.meeting_base_url}")
        
        if license_result.http_status is not None:
            print(f"   HTTP Status: {license_result.http_status}")
        
        if license_result.authorized is not None:
            print(f"   Authorized: {license_result.authorized}")
        
        if license_result.device_type is not None:
            print(f"   Device Type: {license_result.device_type} (expected: {license_result.device_type_expected})")
        
        if license_result.token_count is not None:
            print(f"   Token Count: {license_result.token_count}")
        
        if license_result.checked_at:
            print(f"   Checked At: {license_result.checked_at}")
    
    # Return appropriate exit code
    if license_result.status == MeetingLicenseStatus.VALID:
        return 0
    elif license_result.status == MeetingLicenseStatus.INVALID:
        return 1
    elif license_result.status == MeetingLicenseStatus.CONFIG_ERROR:
        return 2
    else:  # NETWORK_ERROR
        return 3


# =============================================================================
# AUTODIAG HANDLER (Phase 4)
# =============================================================================

def handle_autodiag(
    root: Path,
    as_json: bool = False,
    api_url: str | None = None,
    diag_url: str | None = None,
    skip_cli: bool = False,
    skip_api: bool = False,
    skip_plugins: bool = False,
    timeout: float = 30.0,
) -> int:
    """
    Run autodiagnostic to validate unused function detection.
    
    Args:
        root: Project root path
        as_json: Output as JSON
        api_url: Main API base URL
        diag_url: Diag API base URL
        skip_cli: Skip CLI scenarios
        skip_api: Skip API scenarios
        skip_plugins: Skip plugin scenarios
        timeout: Timeout per scenario in seconds
        
    Returns:
        Exit code (0=success, 1=issues found, 2=errors)
    """
    from jupiter.core.autodiag import run_autodiag_sync, AutodiagStatus
    
    print(f"🔍 Running autodiag on {root}...")
    
    try:
        report = run_autodiag_sync(
            project_root=root,
            api_base_url=api_url,
            diag_base_url=diag_url,
            skip_cli=skip_cli,
            skip_api=skip_api,
            skip_plugins=skip_plugins,
            timeout_seconds=timeout,
        )
        
        if as_json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            # Print human-readable summary
            print()
            print("=" * 60)
            print("AUTODIAG REPORT")
            print("=" * 60)
            print()
            
            # Status
            status_icons = {
                AutodiagStatus.SUCCESS: "✅",
                AutodiagStatus.PARTIAL: "⚠️",
                AutodiagStatus.FAILED: "❌",
                AutodiagStatus.SKIPPED: "⏭️",
            }
            print(f"Status: {status_icons.get(report.status, '❓')} {report.status.value.upper()}")
            print(f"Duration: {report.duration_seconds:.2f}s")
            print()
            
            # Static analysis summary
            print("📊 Static Analysis:")
            print(f"   Total functions: {report.static_total_functions}")
            print(f"   Likely used: {report.static_likely_used_count}")
            print(f"   Possibly unused: {report.static_possibly_unused_count}")
            print(f"   Unused: {report.static_unused_count}")
            print()
            
            # Dynamic validation summary
            print("🔄 Dynamic Validation:")
            print(f"   Scenarios run: {report.scenarios_run}")
            print(f"   Passed: {report.scenarios_passed}")
            print(f"   Failed: {report.scenarios_failed}")
            print()
            
            # False positive detection
            print("🎯 False Positive Detection:")
            print(f"   False positives: {report.false_positive_count}")
            print(f"   True unused: {report.true_unused_count}")
            print(f"   False positive rate: {report.false_positive_rate:.1f}%")
            print()
            
            # Scenario details
            if report.scenario_results:
                print("📋 Scenario Results:")
                for scenario in report.scenario_results:
                    icon = "✅" if scenario.status == "passed" else "❌" if scenario.status == "failed" else "⏭️"
                    print(f"   {icon} {scenario.name}: {scenario.status} ({scenario.duration_seconds:.2f}s)")
                print()
            
            # False positives list
            if report.false_positives:
                print("🔴 False Positives Detected:")
                for i, fp in enumerate(report.false_positives[:10], 1):
                    print(f"   {i}. {fp.function_name} ({fp.file_path})")
                    print(f"      Triggered by: {fp.scenario}")
                if len(report.false_positives) > 10:
                    print(f"   ... and {len(report.false_positives) - 10} more")
                print()
            
            # True unused functions
            if report.true_unused:
                print("🟢 Truly Unused Functions:")
                for i, func in enumerate(report.true_unused[:10], 1):
                    print(f"   {i}. {func}")
                if len(report.true_unused) > 10:
                    print(f"   ... and {len(report.true_unused) - 10} more")
                print()
            
            # Recommendations
            if report.recommendations:
                print("💡 Recommendations:")
                for rec in report.recommendations:
                    print(f"   • {rec}")
                print()
            
            print("=" * 60)
        
        # Return exit code based on status
        if report.status == AutodiagStatus.SUCCESS:
            return 0
        elif report.status == AutodiagStatus.PARTIAL:
            return 1
        else:
            return 2
            
    except Exception as e:
        logger.error("Autodiag failed: %s", e)
        if as_json:
            print(json.dumps({"error": str(e), "status": "failed"}, indent=2))
        else:
            print(f"❌ Autodiag failed: {e}")
        return 2
