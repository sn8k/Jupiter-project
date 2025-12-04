"""Jupiter Plugin Bridge - Core Infrastructure.

Version: 0.23.0 - Added alerting system for threshold-based notifications

The Bridge is the central component of Jupiter's plugin architecture v2.
It provides:
- Plugin discovery and lifecycle management
- Service locator for plugins to access core functionality
- Event bus for plugin communication
- Registry for CLI/API/UI contributions
- Bootstrap for system initialization
- Metrics collection and aggregation
- Background job management
- Legacy plugin adapter
- Permission checking
- Hot reload support
- Plugin signature verification
- Monitoring, audit logging, and rate limiting
- Developer mode for plugin development
- Governance: whitelist/blacklist and feature flags
- Plugin notifications system
- Usage statistics tracking
- Error reporting and diagnostics
- Alerting: threshold-based notifications for metrics

This package contains:
- interfaces.py: ABC interfaces for plugin contracts
- exceptions.py: Dedicated exception classes
- manifest.py: Plugin manifest parsing and validation
- bridge.py: Main Bridge singleton and plugin registry
- services.py: Service locator implementation
- events.py: Event bus for pub/sub
- cli_registry.py: CLI contribution registry
- api_registry.py: API contribution registry  
- ui_registry.py: UI contribution registry
- metrics.py: Metrics collection system
- jobs.py: Background job management
- bootstrap.py: System initialization
- legacy_adapter.py: Compatibility layer for v1 plugins
- permissions.py: Granular permission checking
- hot_reload.py: Dynamic plugin reloading
- signature.py: Cryptographic plugin signing
- monitoring.py: Audit logging, timeouts, rate limiting
- dev_mode.py: Developer mode features
- governance.py: Whitelist/blacklist and feature flags
- notifications.py: Plugin notification system
- usage_stats.py: Plugin usage statistics tracking
- error_report.py: Error reporting and diagnostics
- alerting.py: Threshold-based alerting system
"""

__version__ = "0.23.0"

from jupiter.core.bridge.exceptions import (
    BridgeError,
    PluginError,
    ManifestError,
    DependencyError,
    CircularDependencyError,
    ServiceNotFoundError,
    PermissionDeniedError,
    LifecycleError,
    ValidationError,
    SignatureError,
)

from jupiter.core.bridge.interfaces import (
    IPlugin,
    IPluginManifest,
    IPluginContribution,
    IPluginHealth,
    IPluginMetrics,
    PluginState,
    PluginType,
    Permission,
    UILocation,
    HealthStatus,
    PluginCapabilities,
    CLIContribution,
    APIContribution,
    UIContribution,
    HealthCheckResult,
    PluginMetrics,
    LegacyPlugin,
    ConfigurablePlugin,
)

from jupiter.core.bridge.manifest import (
    PluginManifest,
    generate_manifest_for_legacy,
)

from jupiter.core.bridge.bridge import (
    Bridge,
    PluginInfo,
    ServiceLocator as BridgeServiceLocator,  # Legacy alias
    EventBusProxy,
)

from jupiter.core.bridge.services import (
    PluginLogger,
    SecureRunner,
    ConfigProxy,
    ServiceLocator,
    create_service_locator,
)

from jupiter.core.bridge.plugin_config import (
    PluginConfigManager,
    ProjectPluginRegistry,
)

from jupiter.core.bridge.events import (
    EventBus,
    EventTopic,
    Event,
    Subscription,
    get_event_bus,
    reset_event_bus,
    emit_plugin_loaded,
    emit_plugin_error,
    emit_plugins_ready,
    emit_scan_started,
    emit_scan_progress,
    emit_scan_finished,
    emit_scan_error,
    emit_config_changed,
    emit_job_started,
    emit_job_progress,
    emit_job_completed,
    emit_job_failed,
)

from jupiter.core.bridge.cli_registry import (
    CLIRegistry,
    RegisteredCommand,
    CommandGroup,
    get_cli_registry,
    reset_cli_registry,
)

from jupiter.core.bridge.api_registry import (
    APIRegistry,
    HTTPMethod,
    RegisteredRoute,
    PluginRouter,
    get_api_registry,
    reset_api_registry,
    RoutePermissionConfig,
    PermissionValidationResult,
    APIPermissionValidator,
    require_plugin_permission,
    get_permission_validator,
)

from jupiter.core.bridge.ui_registry import (
    UIRegistry,
    RegisteredPanel,
    RegisteredMenuItem,
    SettingsSchema,
    PluginUIManifest,
    get_ui_registry,
    reset_ui_registry,
)

from jupiter.core.bridge.metrics import (
    MetricsCollector,
    MetricType,
    MetricPoint,
    MetricSummary,
    TimingContext,
    get_metrics_collector,
    init_metrics_collector,
    record_metric,
    increment_counter,
    record_timing,
    timed,
)

from jupiter.core.bridge.jobs import (
    JobManager,
    JobStatus,
    Job,
    CircuitState,
    CircuitBreaker,
    CircuitBreakerRegistry,
    get_job_manager,
    init_job_manager,
    submit_job,
    cancel_job,
    get_job,
    list_jobs,
    export_job,
    export_jobs,
)

from jupiter.core.bridge.legacy_adapter import (
    LegacyAdapter,
    LegacyPluginWrapper,
    LegacyManifest,
    LegacyCapabilities,
    LegacyPluginError,
    is_legacy_plugin,
    is_legacy_ui_plugin,
    get_legacy_adapter,
    init_legacy_adapter,
    shutdown_legacy_adapter,
    discover_legacy_plugins,
)

from jupiter.core.bridge.permissions import (
    PermissionChecker,
    PermissionCheckResult,
    get_permission_checker,
    init_permission_checker,
    require_permission,
)

from jupiter.core.bridge.hot_reload import (
    HotReloader,
    HotReloadError,
    ReloadResult,
    ReloadHistoryEntry,
    get_hot_reloader,
    init_hot_reloader,
    reset_hot_reloader,
    reload_plugin,
    can_reload_plugin,
    get_reload_history,
    get_reload_stats,
)

from jupiter.core.bridge.signature import (
    TrustLevel,
    SignatureAlgorithm,
    SignatureInfo,
    VerificationResult,
    SigningResult,
    TrustedSigner,
    SignatureVerifier,
    PluginSigner,
    get_signature_verifier,
    init_signature_verifier,
    reset_signature_verifier,
    verify_plugin,
    sign_plugin,
    is_plugin_trusted,
)

from jupiter.core.bridge.monitoring import (
    AuditEventType,
    AuditEntry,
    AuditLogger,
    TimeoutError as OperationTimeoutError,
    TimeoutConfig,
    with_timeout,
    sync_with_timeout,
    RateLimitConfig,
    RateLimiter,
    PluginMonitor,
    get_monitor,
    init_monitor,
    reset_monitor,
    audit_log,
    check_rate_limit,
    get_timeout,
)

from jupiter.core.bridge.dev_mode import (
    DevModeConfig,
    DeveloperMode,
    PluginFileHandler,
    get_dev_mode,
    init_dev_mode,
    reset_dev_mode,
    is_dev_mode,
    enable_dev_mode,
    disable_dev_mode,
    get_dev_mode_status,
)

from jupiter.core.bridge.governance import (
    ListMode,
    PolicyAction,
    FeatureFlag,
    PluginPolicy,
    GovernanceConfig,
    PolicyCheckResult as GovernancePolicyCheckResult,
    GovernanceManager,
    get_governance,
    init_governance,
    reset_governance,
    is_plugin_allowed,
    check_plugin_allowed,
    is_feature_enabled,
    add_to_whitelist,
    add_to_blacklist,
    set_feature_flag,
    get_governance_status,
)

from jupiter.core.bridge.notifications import (
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationAction,
    Notification,
    PluginNotificationPreferences,
    NotificationConfig,
    NotificationManager,
    get_notification_manager,
    init_notification_manager,
    reset_notification_manager,
    notify,
    notify_info,
    notify_success,
    notify_warning,
    notify_error,
    get_unread_count,
    get_notifications,
    get_notification_status,
)

from jupiter.core.bridge.usage_stats import (
    TimeFrame,
    ExecutionStatus,
    ExecutionRecord,
    MethodStats,
    PluginStats,
    TimeframeStats,
    UsageStatsConfig,
    ExecutionTimer,
    UsageStatsManager,
    get_usage_stats_manager,
    init_usage_stats_manager,
    reset_usage_stats_manager,
    record_execution,
    time_execution,
    get_plugin_stats as get_plugin_usage_stats,
    get_stats_summary,
)

from jupiter.core.bridge.error_report import (
    ErrorSeverity,
    ErrorCategory,
    ReportFormat,
    SystemInfo,
    PluginContext,
    ErrorContext,
    ErrorReport,
    ErrorReportConfig,
    DataAnonymizer,
    ErrorReportManager,
    get_error_report_manager,
    init_error_report_manager,
    reset_error_report_manager,
    report_error,
    get_error_report,
    get_error_reports,
    get_error_summary,
    export_error_report,
)

from jupiter.core.bridge.alerting import (
    ComparisonOperator,
    AlertSeverity,
    AlertState,
    AlertThreshold,
    Alert,
    AlertingManager,
    get_alerting_manager,
    init_alerting_manager,
    reset_alerting_manager,
    add_threshold,
    remove_threshold,
    check_metric as check_alert_metric,
    check_all as check_all_alerts,
    list_alerts,
    acknowledge_alert,
)

from jupiter.core.bridge.bootstrap import (
    init_plugin_system,
    shutdown_plugin_system,
    is_initialized,
    get_bridge,
    get_plugin_stats,
)

__all__ = [
    # Version
    "__version__",
    # Bridge
    "Bridge",
    "PluginInfo",
    "ServiceLocator",
    "BridgeServiceLocator",  # Legacy alias
    "EventBusProxy",
    # Services
    "PluginLogger",
    "SecureRunner",
    "ConfigProxy",
    "create_service_locator",
    # Plugin Config
    "PluginConfigManager",
    "ProjectPluginRegistry",
    # Exceptions
    "BridgeError",
    "PluginError", 
    "ManifestError",
    "DependencyError",
    "CircularDependencyError",
    "ServiceNotFoundError",
    "PermissionDeniedError",
    "LifecycleError",
    "ValidationError",
    "SignatureError",
    # Interfaces
    "IPlugin",
    "IPluginManifest",
    "IPluginContribution",
    "IPluginHealth",
    "IPluginMetrics",
    "PluginState",
    "PluginType",
    "Permission",
    "UILocation",
    "HealthStatus",
    # Data classes
    "PluginCapabilities",
    "CLIContribution",
    "APIContribution",
    "UIContribution",
    "HealthCheckResult",
    "PluginMetrics",
    # Protocols
    "LegacyPlugin",
    "ConfigurablePlugin",
    # Manifest
    "PluginManifest",
    "generate_manifest_for_legacy",
    # Events
    "EventBus",
    "EventTopic",
    "Event",
    "Subscription",
    "get_event_bus",
    "reset_event_bus",
    "emit_plugin_loaded",
    "emit_plugin_error",
    "emit_scan_started",
    "emit_scan_progress",
    "emit_scan_finished",
    "emit_scan_error",
    "emit_config_changed",
    "emit_job_started",
    "emit_job_progress",
    "emit_job_completed",
    "emit_job_failed",
    # CLI Registry
    "CLIRegistry",
    "RegisteredCommand",
    "CommandGroup",
    "get_cli_registry",
    "reset_cli_registry",
    # API Registry
    "APIRegistry",
    "HTTPMethod",
    "RegisteredRoute",
    "PluginRouter",
    "get_api_registry",
    "reset_api_registry",
    # UI Registry
    "UIRegistry",
    "RegisteredPanel",
    "RegisteredMenuItem",
    "SettingsSchema",
    "PluginUIManifest",
    "get_ui_registry",
    "reset_ui_registry",
    # Metrics
    "MetricsCollector",
    "MetricType",
    "MetricPoint",
    "MetricSummary",
    "TimingContext",
    "get_metrics_collector",
    "init_metrics_collector",
    "record_metric",
    "increment_counter",
    "record_timing",
    "timed",
    # Jobs
    "JobManager",
    "JobStatus",
    "Job",
    "CircuitState",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "get_job_manager",
    "init_job_manager",
    "submit_job",
    "cancel_job",
    "get_job",
    "list_jobs",
    "export_job",
    "export_jobs",
    # Legacy Adapter
    "LegacyAdapter",
    "LegacyPluginWrapper",
    "LegacyManifest",
    "LegacyCapabilities",
    "LegacyPluginError",
    "is_legacy_plugin",
    "is_legacy_ui_plugin",
    "get_legacy_adapter",
    "init_legacy_adapter",
    "shutdown_legacy_adapter",
    "discover_legacy_plugins",
    # Permissions
    "PermissionChecker",
    "PermissionCheckResult",
    "get_permission_checker",
    "init_permission_checker",
    "require_permission",
    # Hot Reload
    "HotReloader",
    "HotReloadError",
    "ReloadResult",
    "ReloadHistoryEntry",
    "get_hot_reloader",
    "init_hot_reloader",
    "reset_hot_reloader",
    "reload_plugin",
    "can_reload_plugin",
    "get_reload_history",
    "get_reload_stats",
    # Signature
    "TrustLevel",
    "SignatureAlgorithm",
    "SignatureInfo",
    "VerificationResult",
    "SigningResult",
    "TrustedSigner",
    "SignatureVerifier",
    "PluginSigner",
    "get_signature_verifier",
    "init_signature_verifier",
    "reset_signature_verifier",
    "verify_plugin",
    "sign_plugin",
    "is_plugin_trusted",
    # Monitoring
    "AuditEventType",
    "AuditEntry",
    "AuditLogger",
    "OperationTimeoutError",
    "TimeoutConfig",
    "with_timeout",
    "sync_with_timeout",
    "RateLimitConfig",
    "RateLimiter",
    "PluginMonitor",
    "get_monitor",
    "init_monitor",
    "reset_monitor",
    "audit_log",
    "check_rate_limit",
    "get_timeout",
    # Developer Mode
    "DevModeConfig",
    "DeveloperMode",
    "PluginFileHandler",
    "get_dev_mode",
    "init_dev_mode",
    "reset_dev_mode",
    "is_dev_mode",
    "enable_dev_mode",
    "disable_dev_mode",
    "get_dev_mode_status",
    # Governance
    "ListMode",
    "PolicyAction",
    "FeatureFlag",
    "PluginPolicy",
    "GovernanceConfig",
    "GovernancePolicyCheckResult",
    "GovernanceManager",
    "get_governance",
    "init_governance",
    "reset_governance",
    "is_plugin_allowed",
    "check_plugin_allowed",
    "is_feature_enabled",
    "add_to_whitelist",
    "add_to_blacklist",
    "set_feature_flag",
    "get_governance_status",
    # Notifications
    "NotificationType",
    "NotificationPriority",
    "NotificationChannel",
    "NotificationAction",
    "Notification",
    "PluginNotificationPreferences",
    "NotificationConfig",
    "NotificationManager",
    "get_notification_manager",
    "init_notification_manager",
    "reset_notification_manager",
    "notify",
    "notify_info",
    "notify_success",
    "notify_warning",
    "notify_error",
    "get_unread_count",
    "get_notifications",
    "get_notification_status",
    # Usage Stats
    "TimeFrame",
    "ExecutionStatus",
    "ExecutionRecord",
    "MethodStats",
    "PluginStats",
    "TimeframeStats",
    "UsageStatsConfig",
    "ExecutionTimer",
    "UsageStatsManager",
    "get_usage_stats_manager",
    "init_usage_stats_manager",
    "reset_usage_stats_manager",
    "record_execution",
    "time_execution",
    "get_plugin_usage_stats",
    "get_stats_summary",
    # Error Reporting
    "ErrorSeverity",
    "ErrorCategory",
    "ReportFormat",
    "SystemInfo",
    "PluginContext",
    "ErrorContext",
    "ErrorReport",
    "ErrorReportConfig",
    "DataAnonymizer",
    "ErrorReportManager",
    "get_error_report_manager",
    "init_error_report_manager",
    "reset_error_report_manager",
    "report_error",
    "get_error_report",
    "get_error_reports",
    "get_error_summary",
    "export_error_report",
    # Alerting
    "ComparisonOperator",
    "AlertSeverity",
    "AlertState",
    "AlertThreshold",
    "Alert",
    "AlertingManager",
    "get_alerting_manager",
    "init_alerting_manager",
    "reset_alerting_manager",
    "add_threshold",
    "remove_threshold",
    "check_alert_metric",
    "check_all_alerts",
    "list_alerts",
    "acknowledge_alert",
    # Bootstrap
    "init_plugin_system",
    "shutdown_plugin_system",
    "is_initialized",
    "get_bridge",
    "get_plugin_stats",
]
