"""
Plugin Error Report Module for Jupiter Bridge.

Provides functionality for generating error reports when critical
errors occur in plugins. Reports are anonymized and can be used
for debugging and support.

Features:
- Capture error context (stacktrace, plugin state, config)
- Anonymize sensitive data (paths, usernames)
- Generate structured reports (JSON, Markdown)
- Report history and deduplication
- Export for support tickets

Version: 0.1.0
"""

__version__ = "0.1.0"

import threading
import time
import json
import hashlib
import logging
import platform
import sys
import traceback
import re
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Set
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity level of an error."""
    LOW = "low"  # Minor issue, plugin still functional
    MEDIUM = "medium"  # Significant issue, some features affected
    HIGH = "high"  # Major issue, plugin mostly non-functional
    CRITICAL = "critical"  # Fatal error, plugin crashed


class ErrorCategory(Enum):
    """Category of error for grouping."""
    INITIALIZATION = "initialization"  # Plugin load/init errors
    CONFIGURATION = "configuration"  # Config parsing/validation errors
    EXECUTION = "execution"  # Runtime execution errors
    DEPENDENCY = "dependency"  # Missing/incompatible dependencies
    PERMISSION = "permission"  # Permission/access errors
    NETWORK = "network"  # Network/connectivity errors
    RESOURCE = "resource"  # Resource exhaustion (memory, disk)
    UNKNOWN = "unknown"  # Unclassified errors


class ReportFormat(Enum):
    """Output format for reports."""
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    MINIMAL = "minimal"  # Just error ID and summary


@dataclass
class SystemInfo:
    """Anonymized system information."""
    os_name: str
    os_version: str
    python_version: str
    jupiter_version: str
    bridge_version: str
    architecture: str
    cpu_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def capture(cls, jupiter_version: str = "unknown", bridge_version: str = "unknown") -> "SystemInfo":
        """Capture current system information."""
        return cls(
            os_name=platform.system(),
            os_version=platform.release(),
            python_version=platform.python_version(),
            jupiter_version=jupiter_version,
            bridge_version=bridge_version,
            architecture=platform.machine(),
            cpu_count=os.cpu_count() or 0
        )


@dataclass
class PluginContext:
    """Context about the plugin that produced the error."""
    plugin_id: str
    plugin_version: str
    plugin_state: str
    method: Optional[str] = None
    execution_time_ms: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    config_hash: Optional[str] = None  # Hash of config for correlation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ErrorContext:
    """Detailed context of the error."""
    error_type: str
    error_message: str
    stacktrace: str
    stacktrace_hash: str  # For deduplication
    locals_snapshot: Dict[str, str] = field(default_factory=dict)  # Anonymized locals
    recent_logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        recent_logs: Optional[List[str]] = None,
        capture_locals: bool = False,
        anonymizer: Optional["DataAnonymizer"] = None
    ) -> "ErrorContext":
        """Create error context from an exception."""
        # Get full stacktrace
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        stacktrace = "".join(tb_lines)
        
        # Anonymize if anonymizer provided
        if anonymizer:
            stacktrace = anonymizer.anonymize_text(stacktrace)
        
        # Create hash for deduplication
        stacktrace_hash = hashlib.sha256(stacktrace.encode()).hexdigest()[:16]
        
        # Capture locals if requested (and anonymize)
        locals_snapshot = {}
        if capture_locals and exc.__traceback__:
            frame = exc.__traceback__.tb_frame
            while frame.f_back:
                frame = frame.f_back
            for key, value in frame.f_locals.items():
                try:
                    value_str = repr(value)[:200]  # Limit size
                    if anonymizer:
                        value_str = anonymizer.anonymize_text(value_str)
                    locals_snapshot[key] = value_str
                except Exception:
                    locals_snapshot[key] = "<unrepresentable>"
        
        error_message = str(exc)
        if anonymizer:
            error_message = anonymizer.anonymize_text(error_message)
        
        return cls(
            error_type=type(exc).__name__,
            error_message=error_message,
            stacktrace=stacktrace,
            stacktrace_hash=stacktrace_hash,
            locals_snapshot=locals_snapshot,
            recent_logs=recent_logs or []
        )


@dataclass
class ErrorReport:
    """Complete error report."""
    report_id: str
    created_at: float
    severity: ErrorSeverity
    category: ErrorCategory
    title: str
    description: str
    system_info: SystemInfo
    plugin_context: PluginContext
    error_context: ErrorContext
    user_notes: str = ""
    reproduction_steps: List[str] = field(default_factory=list)
    related_report_ids: List[str] = field(default_factory=list)  # Similar/duplicate reports
    submitted: bool = False
    submitted_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "system_info": self.system_info.to_dict(),
            "plugin_context": self.plugin_context.to_dict(),
            "error_context": self.error_context.to_dict(),
            "user_notes": self.user_notes,
            "reproduction_steps": self.reproduction_steps,
            "related_report_ids": self.related_report_ids,
            "submitted": self.submitted,
            "submitted_at": self.submitted_at,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorReport":
        """Create from dictionary."""
        system_info = SystemInfo(**data["system_info"])
        plugin_context = PluginContext(**data["plugin_context"])
        error_context = ErrorContext(**data["error_context"])
        
        return cls(
            report_id=data["report_id"],
            created_at=data["created_at"],
            severity=ErrorSeverity(data["severity"]),
            category=ErrorCategory(data["category"]),
            title=data["title"],
            description=data["description"],
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context,
            user_notes=data.get("user_notes", ""),
            reproduction_steps=data.get("reproduction_steps", []),
            related_report_ids=data.get("related_report_ids", []),
            submitted=data.get("submitted", False),
            submitted_at=data.get("submitted_at"),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self, indent: int = 2) -> str:
        """Export to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_markdown(self) -> str:
        """Export to Markdown format."""
        lines = [
            f"# Error Report: {self.report_id}",
            "",
            f"**Created:** {datetime.fromtimestamp(self.created_at).isoformat()}",
            f"**Severity:** {self.severity.value.upper()}",
            f"**Category:** {self.category.value}",
            "",
            "## Summary",
            "",
            f"**{self.title}**",
            "",
            self.description,
            "",
            "## Plugin Information",
            "",
            f"- **Plugin ID:** {self.plugin_context.plugin_id}",
            f"- **Version:** {self.plugin_context.plugin_version}",
            f"- **State:** {self.plugin_context.plugin_state}",
        ]
        
        if self.plugin_context.method:
            lines.append(f"- **Method:** {self.plugin_context.method}")
        
        if self.plugin_context.execution_time_ms:
            lines.append(f"- **Execution Time:** {self.plugin_context.execution_time_ms:.2f}ms")
        
        lines.extend([
            "",
            "## Error Details",
            "",
            f"**Type:** `{self.error_context.error_type}`",
            "",
            f"**Message:** {self.error_context.error_message}",
            "",
            "### Stacktrace",
            "",
            "```",
            self.error_context.stacktrace,
            "```",
            "",
            "## System Information",
            "",
            f"- **OS:** {self.system_info.os_name} {self.system_info.os_version}",
            f"- **Python:** {self.system_info.python_version}",
            f"- **Jupiter:** {self.system_info.jupiter_version}",
            f"- **Bridge:** {self.system_info.bridge_version}",
            f"- **Architecture:** {self.system_info.architecture}",
        ])
        
        if self.user_notes:
            lines.extend([
                "",
                "## User Notes",
                "",
                self.user_notes
            ])
        
        if self.reproduction_steps:
            lines.extend([
                "",
                "## Reproduction Steps",
                ""
            ])
            for i, step in enumerate(self.reproduction_steps, 1):
                lines.append(f"{i}. {step}")
        
        return "\n".join(lines)
    
    def to_text(self) -> str:
        """Export to plain text format."""
        lines = [
            f"=== ERROR REPORT: {self.report_id} ===",
            "",
            f"Created: {datetime.fromtimestamp(self.created_at).isoformat()}",
            f"Severity: {self.severity.value.upper()}",
            f"Category: {self.category.value}",
            "",
            f"TITLE: {self.title}",
            "",
            self.description,
            "",
            "--- Plugin Context ---",
            f"Plugin: {self.plugin_context.plugin_id} v{self.plugin_context.plugin_version}",
            f"State: {self.plugin_context.plugin_state}",
        ]
        
        if self.plugin_context.method:
            lines.append(f"Method: {self.plugin_context.method}")
        
        lines.extend([
            "",
            "--- Error Details ---",
            f"Type: {self.error_context.error_type}",
            f"Message: {self.error_context.error_message}",
            "",
            "Stacktrace:",
            self.error_context.stacktrace,
            "",
            "--- System ---",
            f"OS: {self.system_info.os_name} {self.system_info.os_version}",
            f"Python: {self.system_info.python_version}",
            f"Jupiter: {self.system_info.jupiter_version}"
        ])
        
        return "\n".join(lines)
    
    def to_minimal(self) -> str:
        """Export minimal format (ID and summary only)."""
        return f"[{self.report_id}] {self.severity.value.upper()}: {self.title}"


class DataAnonymizer:
    """
    Anonymizer for sensitive data in error reports.
    
    Removes or replaces:
    - File paths (keeps structure, anonymizes user directories)
    - Usernames
    - IP addresses
    - Email addresses
    - API keys / tokens
    """
    
    def __init__(self):
        """Initialize anonymizer with default patterns."""
        self._patterns: List[tuple] = []
        self._custom_replacements: Dict[str, str] = {}
        self._setup_default_patterns()
    
    def _setup_default_patterns(self) -> None:
        """Set up default anonymization patterns."""
        # Windows user paths - use lambda to avoid escape issues
        self._patterns.append((
            re.compile(r'C:\\Users\\[^\\]+', re.IGNORECASE),
            lambda m: 'C:\\Users\\<USER>'
        ))
        
        # Unix user paths
        self._patterns.append((
            re.compile(r'/home/[^/]+'),
            lambda m: '/home/<USER>'
        ))
        self._patterns.append((
            re.compile(r'/Users/[^/]+'),
            lambda m: '/Users/<USER>'
        ))
        
        # Email addresses
        self._patterns.append((
            re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            lambda m: '<EMAIL>'
        ))
        
        # IP addresses (v4)
        self._patterns.append((
            re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
            lambda m: '<IP_ADDRESS>'
        ))
        
        # API keys / tokens (common patterns) - capture group 1 for prefix
        self._patterns.append((
            re.compile(r'(api[_-]?key|token|secret|password|auth)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{16,}', re.IGNORECASE),
            lambda m: f'{m.group(1)}=<REDACTED>'
        ))
        
        # Bearer tokens
        self._patterns.append((
            re.compile(r'Bearer\s+[a-zA-Z0-9_.-]+', re.IGNORECASE),
            lambda m: 'Bearer <TOKEN>'
        ))
    
    def add_pattern(self, pattern: str, replacement: str) -> None:
        """Add a custom anonymization pattern."""
        self._patterns.append((re.compile(pattern), replacement))
    
    def add_replacement(self, sensitive: str, replacement: str) -> None:
        """Add a direct string replacement."""
        self._custom_replacements[sensitive] = replacement
    
    def anonymize_text(self, text: str) -> str:
        """Anonymize sensitive data in text."""
        result = text
        
        # Apply custom replacements first
        for sensitive, replacement in self._custom_replacements.items():
            result = result.replace(sensitive, replacement)
        
        # Apply regex patterns
        for pattern, replacement in self._patterns:
            result = pattern.sub(replacement, result)
        
        return result
    
    def anonymize_path(self, path: str) -> str:
        """Anonymize a file path while preserving structure."""
        return self.anonymize_text(path)
    
    def anonymize_dict(self, data: Dict[str, Any], deep: bool = True) -> Dict[str, Any]:
        """Anonymize all string values in a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.anonymize_text(value)
            elif isinstance(value, dict) and deep:
                result[key] = self.anonymize_dict(value, deep)
            elif isinstance(value, list) and deep:
                result[key] = [
                    self.anonymize_text(v) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result


@dataclass
class ErrorReportConfig:
    """Configuration for error reporting."""
    enabled: bool = True
    auto_capture: bool = True  # Auto-capture on critical errors
    capture_locals: bool = False  # Capture local variables (privacy risk)
    max_stacktrace_depth: int = 50
    max_recent_logs: int = 20
    anonymize: bool = True
    persist_reports: bool = True
    persistence_path: Optional[Path] = None
    max_stored_reports: int = 100
    dedup_window_hours: int = 24  # Window for deduplication
    jupiter_version: str = "unknown"
    bridge_version: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "auto_capture": self.auto_capture,
            "capture_locals": self.capture_locals,
            "max_stacktrace_depth": self.max_stacktrace_depth,
            "max_recent_logs": self.max_recent_logs,
            "anonymize": self.anonymize,
            "persist_reports": self.persist_reports,
            "persistence_path": str(self.persistence_path) if self.persistence_path else None,
            "max_stored_reports": self.max_stored_reports,
            "dedup_window_hours": self.dedup_window_hours,
            "jupiter_version": self.jupiter_version,
            "bridge_version": self.bridge_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorReportConfig":
        """Create from dictionary."""
        config = cls()
        config.enabled = data.get("enabled", True)
        config.auto_capture = data.get("auto_capture", True)
        config.capture_locals = data.get("capture_locals", False)
        config.max_stacktrace_depth = data.get("max_stacktrace_depth", 50)
        config.max_recent_logs = data.get("max_recent_logs", 20)
        config.anonymize = data.get("anonymize", True)
        config.persist_reports = data.get("persist_reports", True)
        if data.get("persistence_path"):
            config.persistence_path = Path(data["persistence_path"])
        config.max_stored_reports = data.get("max_stored_reports", 100)
        config.dedup_window_hours = data.get("dedup_window_hours", 24)
        config.jupiter_version = data.get("jupiter_version", "unknown")
        config.bridge_version = data.get("bridge_version", "unknown")
        return config


class ErrorReportManager:
    """
    Manager for creating and storing error reports.
    
    Provides:
    - Error report creation from exceptions
    - Automatic anonymization
    - Report deduplication
    - Persistence
    - Export in multiple formats
    """
    
    def __init__(self, config: Optional[ErrorReportConfig] = None):
        """Initialize the error report manager."""
        self.config = config or ErrorReportConfig()
        self._lock = threading.RLock()
        self._reports: Dict[str, ErrorReport] = {}
        self._stacktrace_hashes: Dict[str, str] = {}  # hash -> report_id for dedup
        self._anonymizer = DataAnonymizer()
        self._recent_logs: List[str] = []
        self._submit_callbacks: List[Callable[[ErrorReport], bool]] = []
        
        # Load existing reports
        if self.config.persist_reports and self.config.persistence_path:
            self._load_from_disk()
    
    def _generate_report_id(self) -> str:
        """Generate a unique report ID."""
        timestamp = int(time.time() * 1000)
        random_suffix = hashlib.sha256(os.urandom(16)).hexdigest()[:8]
        return f"ERR-{timestamp}-{random_suffix}"
    
    def _categorize_error(self, error_type: str, error_message: str) -> ErrorCategory:
        """Categorize an error based on type and message."""
        error_lower = f"{error_type} {error_message}".lower()
        
        if any(kw in error_lower for kw in ["import", "module", "dependency", "require"]):
            return ErrorCategory.DEPENDENCY
        
        if any(kw in error_lower for kw in ["permission", "access", "denied", "forbidden"]):
            return ErrorCategory.PERMISSION
        
        if any(kw in error_lower for kw in ["config", "setting", "yaml", "json", "parse"]):
            return ErrorCategory.CONFIGURATION
        
        if any(kw in error_lower for kw in ["init", "setup", "load", "bootstrap"]):
            return ErrorCategory.INITIALIZATION
        
        if any(kw in error_lower for kw in ["network", "connection", "timeout", "socket", "http"]):
            return ErrorCategory.NETWORK
        
        if any(kw in error_lower for kw in ["memory", "disk", "space", "resource", "exhausted"]):
            return ErrorCategory.RESOURCE
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, exc: BaseException, context: Optional[Dict] = None) -> ErrorSeverity:
        """Determine severity based on exception type and context."""
        # Critical exceptions
        if isinstance(exc, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL
        
        # Low for expected/handled exceptions (check before OSError)
        if isinstance(exc, (FileNotFoundError, PermissionError, TimeoutError)):
            return ErrorSeverity.LOW
        
        # High severity for runtime errors
        if isinstance(exc, (RuntimeError, RecursionError, OSError)):
            return ErrorSeverity.HIGH
        
        # Medium for common errors
        if isinstance(exc, (TypeError, ValueError, AttributeError, KeyError)):
            return ErrorSeverity.MEDIUM
        
        # Default to medium
        return ErrorSeverity.MEDIUM
    
    def add_log(self, log_entry: str) -> None:
        """Add a log entry for inclusion in reports."""
        with self._lock:
            self._recent_logs.append(log_entry)
            if len(self._recent_logs) > self.config.max_recent_logs:
                self._recent_logs = self._recent_logs[-self.config.max_recent_logs:]
    
    def create_report(
        self,
        exc: BaseException,
        plugin_id: str,
        plugin_version: str = "unknown",
        plugin_state: str = "unknown",
        method: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        severity: Optional[ErrorSeverity] = None,
        category: Optional[ErrorCategory] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ErrorReport:
        """
        Create an error report from an exception.
        
        Args:
            exc: The exception that occurred
            plugin_id: ID of the plugin that produced the error
            plugin_version: Version of the plugin
            plugin_state: Current state of the plugin
            method: Method where error occurred
            execution_time_ms: Execution time before error
            title: Custom title (auto-generated if not provided)
            description: Custom description
            severity: Override severity detection
            category: Override category detection
            metadata: Additional metadata
            
        Returns:
            The created ErrorReport
        """
        if not self.config.enabled:
            raise RuntimeError("Error reporting is disabled")
        
        with self._lock:
            # Get anonymizer if enabled
            anonymizer = self._anonymizer if self.config.anonymize else None
            
            # Capture error context
            error_context = ErrorContext.from_exception(
                exc,
                recent_logs=list(self._recent_logs),
                capture_locals=self.config.capture_locals,
                anonymizer=anonymizer
            )
            
            # Check for duplicates
            if error_context.stacktrace_hash in self._stacktrace_hashes:
                existing_id = self._stacktrace_hashes[error_context.stacktrace_hash]
                if existing_id in self._reports:
                    existing = self._reports[existing_id]
                    # Check if within dedup window
                    age_hours = (time.time() - existing.created_at) / 3600
                    if age_hours < self.config.dedup_window_hours:
                        # Return existing report with updated metadata
                        existing.metadata["occurrence_count"] = existing.metadata.get("occurrence_count", 1) + 1
                        existing.metadata["last_occurrence"] = time.time()
                        return existing
            
            # Create system info
            system_info = SystemInfo.capture(
                jupiter_version=self.config.jupiter_version,
                bridge_version=self.config.bridge_version
            )
            
            # Create plugin context
            plugin_context = PluginContext(
                plugin_id=plugin_id,
                plugin_version=plugin_version,
                plugin_state=plugin_state,
                method=method,
                execution_time_ms=execution_time_ms
            )
            
            # Determine severity and category
            final_severity = severity or self._determine_severity(exc)
            final_category = category or self._categorize_error(
                error_context.error_type,
                error_context.error_message
            )
            
            # Generate title if not provided
            final_title = title or f"{error_context.error_type} in {plugin_id}"
            
            # Generate description if not provided
            final_description = description or error_context.error_message
            
            # Create report
            report = ErrorReport(
                report_id=self._generate_report_id(),
                created_at=time.time(),
                severity=final_severity,
                category=final_category,
                title=final_title,
                description=final_description,
                system_info=system_info,
                plugin_context=plugin_context,
                error_context=error_context,
                metadata=metadata or {}
            )
            
            # Store report
            self._reports[report.report_id] = report
            self._stacktrace_hashes[error_context.stacktrace_hash] = report.report_id
            
            # Trim if needed
            if len(self._reports) > self.config.max_stored_reports:
                self._trim_old_reports()
            
            logger.info(f"Created error report: {report.report_id}")
            return report
    
    def _trim_old_reports(self) -> None:
        """Remove oldest reports to stay within limit."""
        sorted_reports = sorted(
            self._reports.values(),
            key=lambda r: r.created_at
        )
        
        to_remove = len(sorted_reports) - self.config.max_stored_reports
        for report in sorted_reports[:to_remove]:
            del self._reports[report.report_id]
            # Clean up hash mapping
            hash_to_remove = None
            for hash_val, rid in self._stacktrace_hashes.items():
                if rid == report.report_id:
                    hash_to_remove = hash_val
                    break
            if hash_to_remove:
                del self._stacktrace_hashes[hash_to_remove]
    
    def get_report(self, report_id: str) -> Optional[ErrorReport]:
        """Get a report by ID."""
        with self._lock:
            return self._reports.get(report_id)
    
    def get_all_reports(self) -> List[ErrorReport]:
        """Get all reports."""
        with self._lock:
            return list(self._reports.values())
    
    def get_reports_by_plugin(self, plugin_id: str) -> List[ErrorReport]:
        """Get all reports for a specific plugin."""
        with self._lock:
            return [
                r for r in self._reports.values()
                if r.plugin_context.plugin_id == plugin_id
            ]
    
    def get_reports_by_severity(self, severity: ErrorSeverity) -> List[ErrorReport]:
        """Get all reports with a specific severity."""
        with self._lock:
            return [
                r for r in self._reports.values()
                if r.severity == severity
            ]
    
    def get_reports_by_category(self, category: ErrorCategory) -> List[ErrorReport]:
        """Get all reports in a specific category."""
        with self._lock:
            return [
                r for r in self._reports.values()
                if r.category == category
            ]
    
    def get_unsubmitted_reports(self) -> List[ErrorReport]:
        """Get all reports that haven't been submitted."""
        with self._lock:
            return [
                r for r in self._reports.values()
                if not r.submitted
            ]
    
    def update_report(
        self,
        report_id: str,
        user_notes: Optional[str] = None,
        reproduction_steps: Optional[List[str]] = None
    ) -> bool:
        """Update a report with additional information."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return False
            
            if user_notes is not None:
                report.user_notes = user_notes
            
            if reproduction_steps is not None:
                report.reproduction_steps = reproduction_steps
            
            return True
    
    def mark_submitted(self, report_id: str) -> bool:
        """Mark a report as submitted."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return False
            
            report.submitted = True
            report.submitted_at = time.time()
            return True
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        with self._lock:
            if report_id not in self._reports:
                return False
            
            report = self._reports[report_id]
            del self._reports[report_id]
            
            # Clean up hash mapping
            hash_to_remove = report.error_context.stacktrace_hash
            if hash_to_remove in self._stacktrace_hashes:
                del self._stacktrace_hashes[hash_to_remove]
            
            return True
    
    def export_report(
        self,
        report_id: str,
        format: ReportFormat = ReportFormat.JSON
    ) -> Optional[str]:
        """Export a report in the specified format."""
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return None
            
            if format == ReportFormat.JSON:
                return report.to_json()
            elif format == ReportFormat.MARKDOWN:
                return report.to_markdown()
            elif format == ReportFormat.TEXT:
                return report.to_text()
            elif format == ReportFormat.MINIMAL:
                return report.to_minimal()
            else:
                return report.to_json()
    
    def export_all_reports(self, format: ReportFormat = ReportFormat.JSON) -> str:
        """Export all reports."""
        with self._lock:
            reports = list(self._reports.values())
        
        if format == ReportFormat.JSON:
            return json.dumps([r.to_dict() for r in reports], indent=2)
        elif format == ReportFormat.MARKDOWN:
            return "\n\n---\n\n".join(r.to_markdown() for r in reports)
        elif format == ReportFormat.TEXT:
            return "\n\n".join(r.to_text() for r in reports)
        elif format == ReportFormat.MINIMAL:
            return "\n".join(r.to_minimal() for r in reports)
        else:
            return json.dumps([r.to_dict() for r in reports], indent=2)
    
    def register_submit_callback(
        self,
        callback: Callable[[ErrorReport], bool]
    ) -> None:
        """Register a callback for report submission."""
        self._submit_callbacks.append(callback)
    
    def unregister_submit_callback(
        self,
        callback: Callable[[ErrorReport], bool]
    ) -> None:
        """Unregister a submission callback."""
        if callback in self._submit_callbacks:
            self._submit_callbacks.remove(callback)
    
    def submit_report(self, report_id: str) -> bool:
        """
        Submit a report using registered callbacks.
        
        Returns True if at least one callback succeeded.
        """
        with self._lock:
            report = self._reports.get(report_id)
            if not report:
                return False
            
            if not self._submit_callbacks:
                logger.warning("No submit callbacks registered")
                return False
            
            success = False
            for callback in self._submit_callbacks:
                try:
                    if callback(report):
                        success = True
                except Exception as e:
                    logger.error(f"Submit callback failed: {e}")
            
            if success:
                report.submitted = True
                report.submitted_at = time.time()
            
            return success
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all reports."""
        with self._lock:
            reports = list(self._reports.values())
            
            severity_counts = {s.value: 0 for s in ErrorSeverity}
            category_counts = {c.value: 0 for c in ErrorCategory}
            plugin_counts: Dict[str, int] = {}
            
            for report in reports:
                severity_counts[report.severity.value] += 1
                category_counts[report.category.value] += 1
                plugin_id = report.plugin_context.plugin_id
                plugin_counts[plugin_id] = plugin_counts.get(plugin_id, 0) + 1
            
            return {
                "total_reports": len(reports),
                "unsubmitted": len([r for r in reports if not r.submitted]),
                "severity_counts": severity_counts,
                "category_counts": category_counts,
                "plugin_counts": plugin_counts,
                "most_erroring_plugin": max(plugin_counts.keys(), key=lambda k: plugin_counts[k]) if plugin_counts else None
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get manager status."""
        with self._lock:
            return {
                "enabled": self.config.enabled,
                "total_reports": len(self._reports),
                "callbacks_registered": len(self._submit_callbacks),
                "anonymization_enabled": self.config.anonymize,
                "persistence_enabled": self.config.persist_reports,
                "persistence_path": str(self.config.persistence_path) if self.config.persistence_path else None,
                "recent_logs_count": len(self._recent_logs)
            }
    
    def save_to_disk(self, path: Optional[Path] = None) -> bool:
        """Save reports to disk."""
        save_path = path or self.config.persistence_path
        if not save_path:
            logger.warning("No persistence path configured")
            return False
        
        try:
            save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                data = {
                    "version": __version__,
                    "saved_at": time.time(),
                    "config": self.config.to_dict(),
                    "reports": [r.to_dict() for r in self._reports.values()]
                }
            
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Error reports saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save error reports: {e}")
            return False
    
    def _load_from_disk(self) -> bool:
        """Load reports from disk."""
        if not self.config.persistence_path:
            return False
        
        path = Path(self.config.persistence_path)
        if not path.exists():
            return False
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            with self._lock:
                for report_data in data.get("reports", []):
                    report = ErrorReport.from_dict(report_data)
                    self._reports[report.report_id] = report
                    self._stacktrace_hashes[report.error_context.stacktrace_hash] = report.report_id
            
            logger.debug(f"Loaded {len(self._reports)} error reports from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load error reports: {e}")
            return False
    
    def clear_all_reports(self) -> None:
        """Clear all reports."""
        with self._lock:
            self._reports.clear()
            self._stacktrace_hashes.clear()


# Global manager instance
_manager: Optional[ErrorReportManager] = None
_manager_lock = threading.Lock()


def get_error_report_manager() -> ErrorReportManager:
    """Get the global error report manager instance."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ErrorReportManager()
        return _manager


def init_error_report_manager(
    config: Optional[ErrorReportConfig] = None
) -> ErrorReportManager:
    """Initialize the global error report manager with optional config."""
    global _manager
    with _manager_lock:
        _manager = ErrorReportManager(config)
        return _manager


def reset_error_report_manager() -> None:
    """Reset the global manager (for testing)."""
    global _manager
    with _manager_lock:
        _manager = None


# Convenience functions
def report_error(
    exc: BaseException,
    plugin_id: str,
    plugin_version: str = "unknown",
    plugin_state: str = "unknown",
    method: Optional[str] = None,
    **kwargs
) -> ErrorReport:
    """Create an error report using the global manager."""
    return get_error_report_manager().create_report(
        exc=exc,
        plugin_id=plugin_id,
        plugin_version=plugin_version,
        plugin_state=plugin_state,
        method=method,
        **kwargs
    )


def get_error_report(report_id: str) -> Optional[ErrorReport]:
    """Get an error report by ID."""
    return get_error_report_manager().get_report(report_id)


def get_error_reports() -> List[ErrorReport]:
    """Get all error reports."""
    return get_error_report_manager().get_all_reports()


def get_error_summary() -> Dict[str, Any]:
    """Get error report summary."""
    return get_error_report_manager().get_summary()


def export_error_report(
    report_id: str,
    format: ReportFormat = ReportFormat.JSON
) -> Optional[str]:
    """Export an error report."""
    return get_error_report_manager().export_report(report_id, format)
