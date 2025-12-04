"""
Tests for the Plugin Error Report module.

Tests cover:
- ErrorSeverity and ErrorCategory enums
- SystemInfo capture
- PluginContext and ErrorContext dataclasses
- ErrorReport creation and serialization
- DataAnonymizer functionality
- ErrorReportManager operations
- Report persistence (save/load)
- Global functions
"""

import pytest
import time
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock, patch

from jupiter.core.bridge.error_report import (
    # Enums
    ErrorSeverity,
    ErrorCategory,
    ReportFormat,
    # Dataclasses
    SystemInfo,
    PluginContext,
    ErrorContext,
    ErrorReport,
    ErrorReportConfig,
    # Classes
    DataAnonymizer,
    ErrorReportManager,
    # Global functions
    get_error_report_manager,
    init_error_report_manager,
    reset_error_report_manager,
    report_error,
    get_error_report,
    get_error_reports,
    get_error_summary,
    export_error_report,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def manager():
    """Create a fresh manager for each test."""
    return ErrorReportManager()


@pytest.fixture
def config():
    """Create a test configuration."""
    return ErrorReportConfig(
        enabled=True,
        persist_reports=False,
        max_stored_reports=50,
        anonymize=True
    )


@pytest.fixture
def manager_with_config(config):
    """Create a manager with custom config."""
    return ErrorReportManager(config)


@pytest.fixture(autouse=True)
def reset_global_manager():
    """Reset global manager before each test."""
    reset_error_report_manager()
    yield
    reset_error_report_manager()


@pytest.fixture
def sample_exception():
    """Create a sample exception for testing."""
    try:
        raise ValueError("Test error message")
    except ValueError as e:
        return e


@pytest.fixture
def runtime_exception():
    """Create a RuntimeError for severity testing."""
    try:
        raise RuntimeError("Critical runtime failure")
    except RuntimeError as e:
        return e


@pytest.fixture
def anonymizer():
    """Create a fresh anonymizer."""
    return DataAnonymizer()


# ============================================================================
# ErrorSeverity Tests
# ============================================================================

class TestErrorSeverity:
    """Tests for ErrorSeverity enum."""
    
    def test_severity_values(self):
        """Test all severity values exist."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_severity_from_string(self):
        """Test creating severity from string."""
        assert ErrorSeverity("low") == ErrorSeverity.LOW
        assert ErrorSeverity("critical") == ErrorSeverity.CRITICAL


# ============================================================================
# ErrorCategory Tests
# ============================================================================

class TestErrorCategory:
    """Tests for ErrorCategory enum."""
    
    def test_category_values(self):
        """Test all category values exist."""
        assert ErrorCategory.INITIALIZATION.value == "initialization"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.EXECUTION.value == "execution"
        assert ErrorCategory.DEPENDENCY.value == "dependency"
        assert ErrorCategory.PERMISSION.value == "permission"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.UNKNOWN.value == "unknown"


# ============================================================================
# ReportFormat Tests
# ============================================================================

class TestReportFormat:
    """Tests for ReportFormat enum."""
    
    def test_format_values(self):
        """Test all format values exist."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.MARKDOWN.value == "markdown"
        assert ReportFormat.TEXT.value == "text"
        assert ReportFormat.MINIMAL.value == "minimal"


# ============================================================================
# SystemInfo Tests
# ============================================================================

class TestSystemInfo:
    """Tests for SystemInfo dataclass."""
    
    def test_capture_system_info(self):
        """Test capturing system info."""
        info = SystemInfo.capture(
            jupiter_version="1.0.0",
            bridge_version="0.1.0"
        )
        assert info.jupiter_version == "1.0.0"
        assert info.bridge_version == "0.1.0"
        assert info.os_name != ""
        assert info.python_version != ""
    
    def test_system_info_to_dict(self):
        """Test conversion to dictionary."""
        info = SystemInfo.capture()
        data = info.to_dict()
        assert "os_name" in data
        assert "python_version" in data
        assert "architecture" in data


# ============================================================================
# PluginContext Tests
# ============================================================================

class TestPluginContext:
    """Tests for PluginContext dataclass."""
    
    def test_create_plugin_context(self):
        """Test creating plugin context."""
        ctx = PluginContext(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            plugin_state="running",
            method="process"
        )
        assert ctx.plugin_id == "test-plugin"
        assert ctx.method == "process"
    
    def test_plugin_context_to_dict(self):
        """Test conversion to dictionary."""
        ctx = PluginContext(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            plugin_state="running"
        )
        data = ctx.to_dict()
        assert data["plugin_id"] == "test-plugin"
        assert data["plugin_version"] == "1.0.0"


# ============================================================================
# ErrorContext Tests
# ============================================================================

class TestErrorContext:
    """Tests for ErrorContext dataclass."""
    
    def test_create_from_exception(self, sample_exception):
        """Test creating error context from exception."""
        ctx = ErrorContext.from_exception(sample_exception)
        assert ctx.error_type == "ValueError"
        assert "Test error message" in ctx.error_message
        assert ctx.stacktrace_hash != ""
        assert "ValueError" in ctx.stacktrace
    
    def test_error_context_with_anonymizer(self, sample_exception, anonymizer):
        """Test error context with anonymization."""
        ctx = ErrorContext.from_exception(
            sample_exception,
            anonymizer=anonymizer
        )
        assert ctx.error_type == "ValueError"
    
    def test_error_context_to_dict(self, sample_exception):
        """Test conversion to dictionary."""
        ctx = ErrorContext.from_exception(sample_exception)
        data = ctx.to_dict()
        assert data["error_type"] == "ValueError"
        assert "stacktrace_hash" in data


# ============================================================================
# ErrorReport Tests
# ============================================================================

class TestErrorReport:
    """Tests for ErrorReport dataclass."""
    
    def test_create_error_report(self, sample_exception):
        """Test creating a complete error report."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            plugin_state="running"
        )
        error_context = ErrorContext.from_exception(sample_exception)
        
        report = ErrorReport(
            report_id="ERR-123",
            created_at=time.time(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXECUTION,
            title="Test Error",
            description="A test error occurred",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        assert report.report_id == "ERR-123"
        assert report.severity == ErrorSeverity.MEDIUM
        assert report.submitted is False
    
    def test_report_to_dict(self, sample_exception):
        """Test conversion to dictionary."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            plugin_state="running"
        )
        error_context = ErrorContext.from_exception(sample_exception)
        
        report = ErrorReport(
            report_id="ERR-123",
            created_at=time.time(),
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXECUTION,
            title="Test Error",
            description="Description",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        data = report.to_dict()
        assert data["report_id"] == "ERR-123"
        assert data["severity"] == "high"
        assert "system_info" in data
    
    def test_report_from_dict(self, sample_exception):
        """Test creating from dictionary."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext(
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            plugin_state="running"
        )
        error_context = ErrorContext.from_exception(sample_exception)
        
        original = ErrorReport(
            report_id="ERR-456",
            created_at=time.time(),
            severity=ErrorSeverity.LOW,
            category=ErrorCategory.CONFIGURATION,
            title="Config Error",
            description="Config failed",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        data = original.to_dict()
        restored = ErrorReport.from_dict(data)
        
        assert restored.report_id == original.report_id
        assert restored.severity == original.severity
        assert restored.category == original.category
    
    def test_report_to_json(self, sample_exception):
        """Test JSON export."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext("test", "1.0", "running")
        error_context = ErrorContext.from_exception(sample_exception)
        
        report = ErrorReport(
            report_id="ERR-789",
            created_at=time.time(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXECUTION,
            title="Test",
            description="Desc",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["report_id"] == "ERR-789"
    
    def test_report_to_markdown(self, sample_exception):
        """Test Markdown export."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext("test", "1.0", "running")
        error_context = ErrorContext.from_exception(sample_exception)
        
        report = ErrorReport(
            report_id="ERR-MD",
            created_at=time.time(),
            severity=ErrorSeverity.HIGH,
            category=ErrorCategory.EXECUTION,
            title="Markdown Test",
            description="Testing markdown export",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        md = report.to_markdown()
        assert "# Error Report: ERR-MD" in md
        assert "**Severity:** HIGH" in md
        assert "## Plugin Information" in md
    
    def test_report_to_text(self, sample_exception):
        """Test plain text export."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext("test", "1.0", "running")
        error_context = ErrorContext.from_exception(sample_exception)
        
        report = ErrorReport(
            report_id="ERR-TXT",
            created_at=time.time(),
            severity=ErrorSeverity.MEDIUM,
            category=ErrorCategory.EXECUTION,
            title="Text Test",
            description="Testing text export",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        txt = report.to_text()
        assert "=== ERROR REPORT: ERR-TXT ===" in txt
        assert "TITLE: Text Test" in txt
    
    def test_report_to_minimal(self, sample_exception):
        """Test minimal export."""
        system_info = SystemInfo.capture()
        plugin_context = PluginContext("test", "1.0", "running")
        error_context = ErrorContext.from_exception(sample_exception)
        
        report = ErrorReport(
            report_id="ERR-MIN",
            created_at=time.time(),
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.EXECUTION,
            title="Minimal Test",
            description="Desc",
            system_info=system_info,
            plugin_context=plugin_context,
            error_context=error_context
        )
        
        minimal = report.to_minimal()
        assert "[ERR-MIN]" in minimal
        assert "CRITICAL" in minimal
        assert "Minimal Test" in minimal


# ============================================================================
# DataAnonymizer Tests
# ============================================================================

class TestDataAnonymizer:
    """Tests for DataAnonymizer class."""
    
    def test_anonymize_windows_path(self, anonymizer):
        """Test anonymizing Windows user paths."""
        text = r"Error in C:\Users\john\project\file.py"
        result = anonymizer.anonymize_text(text)
        assert "john" not in result
        assert "<USER>" in result
    
    def test_anonymize_unix_path(self, anonymizer):
        """Test anonymizing Unix user paths."""
        text = "Error in /home/alice/project/file.py"
        result = anonymizer.anonymize_text(text)
        assert "alice" not in result
        assert "<USER>" in result
    
    def test_anonymize_mac_path(self, anonymizer):
        """Test anonymizing macOS user paths."""
        text = "Error in /Users/bob/Documents/code.py"
        result = anonymizer.anonymize_text(text)
        assert "bob" not in result
        assert "<USER>" in result
    
    def test_anonymize_email(self, anonymizer):
        """Test anonymizing email addresses."""
        text = "Contact: user@example.com for support"
        result = anonymizer.anonymize_text(text)
        assert "user@example.com" not in result
        assert "<EMAIL>" in result
    
    def test_anonymize_ip_address(self, anonymizer):
        """Test anonymizing IP addresses."""
        text = "Connected to 192.168.1.100 on port 8080"
        result = anonymizer.anonymize_text(text)
        assert "192.168.1.100" not in result
        assert "<IP_ADDRESS>" in result
    
    def test_anonymize_api_key(self, anonymizer):
        """Test anonymizing API keys."""
        text = 'api_key = "sk_test_1234567890abcdefgh"'
        result = anonymizer.anonymize_text(text)
        assert "sk_test_1234567890abcdefgh" not in result
        assert "<REDACTED>" in result
    
    def test_anonymize_bearer_token(self, anonymizer):
        """Test anonymizing Bearer tokens."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = anonymizer.anonymize_text(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "<TOKEN>" in result
    
    def test_add_custom_pattern(self, anonymizer):
        """Test adding custom anonymization pattern."""
        anonymizer.add_pattern(r"secret_\d+", "<SECRET>")
        text = "The code is secret_12345"
        result = anonymizer.anonymize_text(text)
        assert "secret_12345" not in result
        assert "<SECRET>" in result
    
    def test_add_direct_replacement(self, anonymizer):
        """Test adding direct string replacement."""
        anonymizer.add_replacement("MySecretValue", "<HIDDEN>")
        text = "The value is MySecretValue"
        result = anonymizer.anonymize_text(text)
        assert "MySecretValue" not in result
        assert "<HIDDEN>" in result
    
    def test_anonymize_dict(self, anonymizer):
        """Test anonymizing dictionary values."""
        data = {
            "path": r"C:\Users\john\file.py",
            "email": "test@example.com",
            "nested": {
                "ip": "10.0.0.1"
            }
        }
        result = anonymizer.anonymize_dict(data)
        assert "john" not in result["path"]
        assert "test@example.com" not in result["email"]
        assert "10.0.0.1" not in result["nested"]["ip"]


# ============================================================================
# ErrorReportConfig Tests
# ============================================================================

class TestErrorReportConfig:
    """Tests for ErrorReportConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = ErrorReportConfig()
        assert config.enabled is True
        assert config.auto_capture is True
        assert config.anonymize is True
        assert config.max_stored_reports == 100
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = ErrorReportConfig(
            enabled=False,
            capture_locals=True,
            max_stored_reports=50
        )
        assert config.enabled is False
        assert config.capture_locals is True
        assert config.max_stored_reports == 50
    
    def test_config_to_dict(self):
        """Test conversion to dictionary."""
        config = ErrorReportConfig(enabled=True, anonymize=False)
        data = config.to_dict()
        assert data["enabled"] is True
        assert data["anonymize"] is False
    
    def test_config_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "enabled": False,
            "capture_locals": True,
            "max_stored_reports": 25
        }
        config = ErrorReportConfig.from_dict(data)
        assert config.enabled is False
        assert config.capture_locals is True
        assert config.max_stored_reports == 25


# ============================================================================
# ErrorReportManager Tests
# ============================================================================

class TestErrorReportManager:
    """Tests for ErrorReportManager."""
    
    def test_create_manager(self):
        """Test manager creation."""
        manager = ErrorReportManager()
        assert manager is not None
        assert manager.config.enabled is True
    
    def test_create_with_config(self, config):
        """Test manager creation with config."""
        manager = ErrorReportManager(config)
        assert manager.config.enabled is True
        assert manager.config.max_stored_reports == 50
    
    def test_create_report(self, manager, sample_exception):
        """Test creating a report."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin",
            plugin_version="1.0.0",
            plugin_state="running"
        )
        
        assert report is not None
        assert report.report_id.startswith("ERR-")
        assert report.plugin_context.plugin_id == "test-plugin"
    
    def test_create_report_disabled(self, sample_exception):
        """Test creating report when disabled."""
        config = ErrorReportConfig(enabled=False)
        manager = ErrorReportManager(config)
        
        with pytest.raises(RuntimeError, match="disabled"):
            manager.create_report(
                exc=sample_exception,
                plugin_id="test-plugin"
            )
    
    def test_create_report_with_custom_severity(self, manager, sample_exception):
        """Test creating report with custom severity."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin",
            severity=ErrorSeverity.CRITICAL
        )
        
        assert report.severity == ErrorSeverity.CRITICAL
    
    def test_create_report_with_custom_category(self, manager, sample_exception):
        """Test creating report with custom category."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin",
            category=ErrorCategory.DEPENDENCY
        )
        
        assert report.category == ErrorCategory.DEPENDENCY
    
    def test_get_report(self, manager, sample_exception):
        """Test getting a report by ID."""
        created = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        retrieved = manager.get_report(created.report_id)
        assert retrieved is not None
        assert retrieved.report_id == created.report_id
    
    def test_get_nonexistent_report(self, manager):
        """Test getting nonexistent report."""
        report = manager.get_report("nonexistent")
        assert report is None
    
    def test_get_all_reports(self, manager):
        """Test getting all reports."""
        try:
            raise ValueError("Error for plugin1")
        except ValueError as e1:
            manager.create_report(exc=e1, plugin_id="plugin1")
        
        try:
            raise TypeError("Error for plugin2")
        except TypeError as e2:
            manager.create_report(exc=e2, plugin_id="plugin2")
        
        reports = manager.get_all_reports()
        assert len(reports) == 2
    
    def test_get_reports_by_plugin(self, manager):
        """Test getting reports by plugin."""
        for i in range(3):
            try:
                raise ValueError(f"Error {i}")
            except ValueError as e:
                plugin_id = "plugin1" if i < 2 else "plugin2"
                manager.create_report(exc=e, plugin_id=plugin_id)
        
        reports = manager.get_reports_by_plugin("plugin1")
        assert len(reports) == 2
    
    def test_get_reports_by_severity(self, manager, sample_exception, runtime_exception):
        """Test getting reports by severity."""
        manager.create_report(
            exc=sample_exception,
            plugin_id="plugin1",
            severity=ErrorSeverity.LOW
        )
        manager.create_report(
            exc=runtime_exception,
            plugin_id="plugin2",
            severity=ErrorSeverity.CRITICAL
        )
        
        critical_reports = manager.get_reports_by_severity(ErrorSeverity.CRITICAL)
        assert len(critical_reports) == 1
    
    def test_get_reports_by_category(self, manager, sample_exception):
        """Test getting reports by category."""
        manager.create_report(
            exc=sample_exception,
            plugin_id="plugin1",
            category=ErrorCategory.NETWORK
        )
        manager.create_report(
            exc=sample_exception,
            plugin_id="plugin2",
            category=ErrorCategory.CONFIGURATION
        )
        
        network_reports = manager.get_reports_by_category(ErrorCategory.NETWORK)
        assert len(network_reports) == 1
    
    def test_update_report(self, manager, sample_exception):
        """Test updating a report."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        result = manager.update_report(
            report.report_id,
            user_notes="This happened when I clicked the button",
            reproduction_steps=["Step 1", "Step 2"]
        )
        
        assert result is True
        updated = manager.get_report(report.report_id)
        assert "clicked the button" in updated.user_notes
        assert len(updated.reproduction_steps) == 2
    
    def test_mark_submitted(self, manager, sample_exception):
        """Test marking report as submitted."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        assert report.submitted is False
        
        result = manager.mark_submitted(report.report_id)
        assert result is True
        
        updated = manager.get_report(report.report_id)
        assert updated.submitted is True
        assert updated.submitted_at is not None
    
    def test_delete_report(self, manager, sample_exception):
        """Test deleting a report."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        result = manager.delete_report(report.report_id)
        assert result is True
        
        deleted = manager.get_report(report.report_id)
        assert deleted is None
    
    def test_delete_nonexistent_report(self, manager):
        """Test deleting nonexistent report."""
        result = manager.delete_report("nonexistent")
        assert result is False
    
    def test_export_report_json(self, manager, sample_exception):
        """Test exporting report as JSON."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        exported = manager.export_report(report.report_id, ReportFormat.JSON)
        assert exported is not None
        parsed = json.loads(exported)
        assert parsed["report_id"] == report.report_id
    
    def test_export_report_markdown(self, manager, sample_exception):
        """Test exporting report as Markdown."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        exported = manager.export_report(report.report_id, ReportFormat.MARKDOWN)
        assert "# Error Report:" in exported
    
    def test_export_all_reports(self, manager):
        """Test exporting all reports."""
        try:
            raise ValueError("Error 1")
        except ValueError as e1:
            manager.create_report(exc=e1, plugin_id="plugin1")
        
        try:
            raise TypeError("Error 2")
        except TypeError as e2:
            manager.create_report(exc=e2, plugin_id="plugin2")
        
        exported = manager.export_all_reports(ReportFormat.JSON)
        parsed = json.loads(exported)
        assert len(parsed) == 2
    
    def test_get_summary(self, manager):
        """Test getting report summary."""
        try:
            raise ValueError("Low severity error 1")
        except ValueError as e1:
            manager.create_report(
                exc=e1,
                plugin_id="plugin1",
                severity=ErrorSeverity.LOW
            )
        
        try:
            raise RuntimeError("Critical error")
        except RuntimeError as e2:
            manager.create_report(
                exc=e2,
                plugin_id="plugin1",
                severity=ErrorSeverity.CRITICAL
            )
        
        try:
            raise TypeError("Low severity error 2")
        except TypeError as e3:
            manager.create_report(
                exc=e3,
                plugin_id="plugin2",
                severity=ErrorSeverity.LOW
            )
        
        summary = manager.get_summary()
        assert summary["total_reports"] == 3
        assert summary["severity_counts"]["low"] == 2
        assert summary["severity_counts"]["critical"] == 1
        assert summary["most_erroring_plugin"] == "plugin1"
    
    def test_get_status(self, manager):
        """Test getting manager status."""
        status = manager.get_status()
        assert status["enabled"] is True
        assert status["total_reports"] == 0
    
    def test_add_log(self, manager, sample_exception):
        """Test adding logs for inclusion in reports."""
        manager.add_log("INFO: Starting process")
        manager.add_log("DEBUG: Processing item 1")
        
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        assert len(report.error_context.recent_logs) == 2
    
    def test_deduplication(self, manager, sample_exception):
        """Test report deduplication."""
        report1 = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        # Same exception should be deduplicated
        report2 = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        # Should return same report
        assert report1.report_id == report2.report_id
        assert report2.metadata.get("occurrence_count", 1) > 1
    
    def test_max_stored_reports(self):
        """Test maximum stored reports limit."""
        config = ErrorReportConfig(max_stored_reports=5)
        manager = ErrorReportManager(config)
        
        # Create different exceptions to avoid deduplication
        for i in range(10):
            try:
                raise ValueError(f"Error {i}")
            except ValueError as e:
                manager.create_report(exc=e, plugin_id=f"plugin{i}")
        
        reports = manager.get_all_reports()
        assert len(reports) <= 5
    
    def test_clear_all_reports(self, manager):
        """Test clearing all reports."""
        try:
            raise ValueError("Error 1")
        except ValueError as e1:
            manager.create_report(exc=e1, plugin_id="plugin1")
        
        try:
            raise TypeError("Error 2")
        except TypeError as e2:
            manager.create_report(exc=e2, plugin_id="plugin2")
        
        manager.clear_all_reports()
        
        reports = manager.get_all_reports()
        assert len(reports) == 0
    
    def test_submit_callback(self, manager, sample_exception):
        """Test submit callback functionality."""
        callback_data = []
        
        def callback(report):
            callback_data.append(report.report_id)
            return True
        
        manager.register_submit_callback(callback)
        
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        result = manager.submit_report(report.report_id)
        assert result is True
        assert report.report_id in callback_data
        
        updated = manager.get_report(report.report_id)
        assert updated.submitted is True


# ============================================================================
# Persistence Tests
# ============================================================================

class TestPersistence:
    """Tests for save/load functionality."""
    
    def test_save_to_disk(self, sample_exception):
        """Test saving reports to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reports.json"
            config = ErrorReportConfig(
                persist_reports=True,
                persistence_path=path
            )
            manager = ErrorReportManager(config)
            
            manager.create_report(
                exc=sample_exception,
                plugin_id="test-plugin"
            )
            
            result = manager.save_to_disk()
            assert result is True
            assert path.exists()
    
    def test_load_from_disk(self, sample_exception):
        """Test loading reports from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "reports.json"
            
            # Create and save
            config1 = ErrorReportConfig(
                persist_reports=True,
                persistence_path=path
            )
            manager1 = ErrorReportManager(config1)
            report = manager1.create_report(
                exc=sample_exception,
                plugin_id="test-plugin"
            )
            manager1.save_to_disk()
            
            # Load in new manager
            config2 = ErrorReportConfig(
                persist_reports=True,
                persistence_path=path
            )
            manager2 = ErrorReportManager(config2)
            
            loaded = manager2.get_report(report.report_id)
            assert loaded is not None
            assert loaded.plugin_context.plugin_id == "test-plugin"
    
    def test_save_without_path(self, manager):
        """Test saving without path configured."""
        result = manager.save_to_disk()
        assert result is False


# ============================================================================
# Severity Detection Tests
# ============================================================================

class TestSeverityDetection:
    """Tests for automatic severity detection."""
    
    def test_memory_error_critical(self, manager):
        """Test MemoryError gets critical severity."""
        try:
            raise MemoryError("Out of memory")
        except MemoryError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.severity == ErrorSeverity.CRITICAL
    
    def test_runtime_error_high(self, manager):
        """Test RuntimeError gets high severity."""
        try:
            raise RuntimeError("Runtime failure")
        except RuntimeError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.severity == ErrorSeverity.HIGH
    
    def test_value_error_medium(self, manager):
        """Test ValueError gets medium severity."""
        try:
            raise ValueError("Invalid value")
        except ValueError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.severity == ErrorSeverity.MEDIUM
    
    def test_file_not_found_low(self, manager):
        """Test FileNotFoundError gets low severity."""
        try:
            raise FileNotFoundError("File missing")
        except FileNotFoundError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.severity == ErrorSeverity.LOW


# ============================================================================
# Category Detection Tests
# ============================================================================

class TestCategoryDetection:
    """Tests for automatic category detection."""
    
    def test_import_error_dependency(self, manager):
        """Test ImportError gets dependency category."""
        try:
            raise ImportError("Module not found")
        except ImportError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.category == ErrorCategory.DEPENDENCY
    
    def test_permission_error_permission(self, manager):
        """Test PermissionError gets permission category."""
        try:
            raise PermissionError("Access denied")
        except PermissionError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.category == ErrorCategory.PERMISSION
    
    def test_config_error_configuration(self, manager):
        """Test config-related error gets configuration category."""
        try:
            raise ValueError("Invalid config setting")
        except ValueError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.category == ErrorCategory.CONFIGURATION
    
    def test_network_error_network(self, manager):
        """Test network-related error gets network category."""
        try:
            raise ConnectionError("Connection timeout")
        except ConnectionError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report.category == ErrorCategory.NETWORK


# ============================================================================
# Thread Safety Tests
# ============================================================================

class TestThreadSafety:
    """Tests for thread safety."""
    
    def test_concurrent_report_creation(self, manager):
        """Test concurrent report creation."""
        results = []
        errors = []
        
        def create_reports(plugin_id):
            for i in range(10):
                try:
                    exc = ValueError(f"Error {plugin_id}-{i}")
                    report = manager.create_report(exc=exc, plugin_id=plugin_id)
                    results.append(report.report_id)
                except Exception as e:
                    errors.append(e)
        
        threads = [
            threading.Thread(target=create_reports, args=(f"plugin{i}",))
            for i in range(5)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        # Not all will be unique due to deduplication
        assert len(results) > 0


# ============================================================================
# Global Functions Tests
# ============================================================================

class TestGlobalFunctions:
    """Tests for global convenience functions."""
    
    def test_get_error_report_manager(self):
        """Test getting global manager."""
        manager = get_error_report_manager()
        assert manager is not None
        
        # Same instance
        manager2 = get_error_report_manager()
        assert manager is manager2
    
    def test_init_error_report_manager(self):
        """Test initializing global manager."""
        config = ErrorReportConfig(enabled=True, max_stored_reports=25)
        manager = init_error_report_manager(config)
        
        assert manager.config.max_stored_reports == 25
        assert get_error_report_manager() is manager
    
    def test_reset_error_report_manager(self):
        """Test resetting global manager."""
        manager1 = get_error_report_manager()
        reset_error_report_manager()
        manager2 = get_error_report_manager()
        
        assert manager1 is not manager2
    
    def test_report_error_global(self, sample_exception):
        """Test global report_error function."""
        report = report_error(
            exc=sample_exception,
            plugin_id="test-plugin",
            plugin_version="1.0.0"
        )
        
        assert report.plugin_context.plugin_id == "test-plugin"
    
    def test_get_error_report_global(self, sample_exception):
        """Test global get_error_report function."""
        created = report_error(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        retrieved = get_error_report(created.report_id)
        assert retrieved is not None
        assert retrieved.report_id == created.report_id
    
    def test_get_error_reports_global(self, sample_exception):
        """Test global get_error_reports function."""
        report_error(exc=sample_exception, plugin_id="plugin1")
        
        reports = get_error_reports()
        assert len(reports) >= 1
    
    def test_get_error_summary_global(self, sample_exception):
        """Test global get_error_summary function."""
        report_error(exc=sample_exception, plugin_id="test-plugin")
        
        summary = get_error_summary()
        assert summary["total_reports"] >= 1
    
    def test_export_error_report_global(self, sample_exception):
        """Test global export_error_report function."""
        report = report_error(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        exported = export_error_report(report.report_id, ReportFormat.JSON)
        assert exported is not None
        assert report.report_id in exported


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_plugin_id(self, manager, sample_exception):
        """Test with empty plugin ID."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id=""
        )
        assert report.plugin_context.plugin_id == ""
    
    def test_unicode_in_error(self, manager):
        """Test with unicode in error message."""
        try:
            raise ValueError("Error with émojis 🎉 and 日本語")
        except ValueError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert "émojis" in report.error_context.error_message or "<" in report.error_context.error_message
    
    def test_very_long_stacktrace(self, manager):
        """Test with very long stacktrace."""
        def recursive_error(depth):
            if depth <= 0:
                raise ValueError("Deep error")
            return recursive_error(depth - 1)
        
        try:
            recursive_error(50)
        except ValueError as e:
            report = manager.create_report(exc=e, plugin_id="test")
            assert report is not None
    
    def test_export_nonexistent_report(self, manager):
        """Test exporting nonexistent report."""
        result = manager.export_report("nonexistent", ReportFormat.JSON)
        assert result is None
    
    def test_update_nonexistent_report(self, manager):
        """Test updating nonexistent report."""
        result = manager.update_report("nonexistent", user_notes="test")
        assert result is False
    
    def test_submit_without_callbacks(self, manager, sample_exception):
        """Test submitting without callbacks."""
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        result = manager.submit_report(report.report_id)
        assert result is False
    
    def test_unregister_callback(self, manager, sample_exception):
        """Test unregistering callbacks."""
        callback = Mock(return_value=True)
        manager.register_submit_callback(callback)
        manager.unregister_submit_callback(callback)
        
        report = manager.create_report(
            exc=sample_exception,
            plugin_id="test-plugin"
        )
        
        result = manager.submit_report(report.report_id)
        assert result is False
        callback.assert_not_called()
