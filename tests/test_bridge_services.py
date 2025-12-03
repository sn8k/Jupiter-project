"""Tests for jupiter.core.bridge.services module.

Version: 0.1.0

Tests for the Service Locator and service wrappers.
"""

import logging
import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from jupiter.core.bridge.services import (
    PluginLogger,
    SecureRunner,
    ConfigProxy,
    ServiceLocator,
    create_service_locator,
)
from jupiter.core.bridge.interfaces import Permission
from jupiter.core.bridge.exceptions import (
    PermissionDeniedError,
    ServiceNotFoundError,
)


# =============================================================================
# PluginLogger Tests
# =============================================================================

class TestPluginLogger:
    """Tests for PluginLogger class."""
    
    def test_creates_logger_with_plugin_prefix(self):
        """Logger should use plugin-specific name."""
        plugin_logger = PluginLogger("test_plugin")
        assert plugin_logger.plugin_id == "test_plugin"
    
    def test_formats_message_with_prefix(self):
        """Messages should be prefixed with plugin ID."""
        plugin_logger = PluginLogger("my_plugin")
        formatted = plugin_logger._format_msg("Hello world")
        assert formatted == "[plugin:my_plugin] Hello world"
    
    def test_debug_logs_with_prefix(self, caplog):
        """Debug messages should include prefix."""
        with caplog.at_level(logging.DEBUG):
            plugin_logger = PluginLogger("debug_test")
            plugin_logger.debug("Test message")
            
            assert "[plugin:debug_test]" in caplog.text
            assert "Test message" in caplog.text
    
    def test_info_logs_with_prefix(self, caplog):
        """Info messages should include prefix."""
        with caplog.at_level(logging.INFO):
            plugin_logger = PluginLogger("info_test")
            plugin_logger.info("Info message")
            
            assert "[plugin:info_test]" in caplog.text
    
    def test_warning_logs_with_prefix(self, caplog):
        """Warning messages should include prefix."""
        with caplog.at_level(logging.WARNING):
            plugin_logger = PluginLogger("warn_test")
            plugin_logger.warning("Warning message")
            
            assert "[plugin:warn_test]" in caplog.text
    
    def test_error_logs_with_prefix(self, caplog):
        """Error messages should include prefix."""
        with caplog.at_level(logging.ERROR):
            plugin_logger = PluginLogger("error_test")
            plugin_logger.error("Error message")
            
            assert "[plugin:error_test]" in caplog.text
    
    def test_set_level(self):
        """Should be able to set logging level."""
        plugin_logger = PluginLogger("level_test")
        plugin_logger.setLevel(logging.WARNING)
        assert plugin_logger.getEffectiveLevel() == logging.WARNING


# =============================================================================
# SecureRunner Tests
# =============================================================================

class TestSecureRunner:
    """Tests for SecureRunner class."""
    
    def test_requires_run_commands_permission(self):
        """Should raise PermissionDeniedError without run_commands."""
        runner = SecureRunner(
            plugin_id="test",
            permissions=[Permission.FS_READ],  # No RUN_COMMANDS
        )
        
        with pytest.raises(PermissionDeniedError) as exc_info:
            runner.run(["echo", "test"])
        
        assert "run commands" in str(exc_info.value).lower()
    
    def test_allows_with_permission(self):
        """Should allow command with run_commands permission."""
        runner = SecureRunner(
            plugin_id="test",
            permissions=[Permission.RUN_COMMANDS],
        )
        
        with patch("jupiter.core.runner.run_command") as mock_run:
            with patch("jupiter.core.state.load_last_root", return_value=Path(".")):
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                result = runner.run(["echo", "test"])
                mock_run.assert_called_once()
    
    def test_enforces_allow_list(self):
        """Should reject commands not in allow-list."""
        runner = SecureRunner(
            plugin_id="test",
            permissions=[Permission.RUN_COMMANDS],
            allowed_commands=["echo", "python"],
        )
        
        with pytest.raises(PermissionDeniedError) as exc_info:
            runner.run(["rm", "-rf", "/"])
        
        assert "allow-list" in str(exc_info.value).lower()
    
    def test_allows_commands_in_allow_list(self):
        """Should allow commands matching allow-list prefix."""
        runner = SecureRunner(
            plugin_id="test",
            permissions=[Permission.RUN_COMMANDS],
            allowed_commands=["echo", "python"],
        )
        
        with patch("jupiter.core.runner.run_command") as mock_run:
            with patch("jupiter.core.state.load_last_root", return_value=Path(".")):
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                runner.run(["echo", "hello"])
                mock_run.assert_called_once()
    
    def test_empty_allow_list_allows_all(self):
        """Empty allow-list should permit all commands."""
        runner = SecureRunner(
            plugin_id="test",
            permissions=[Permission.RUN_COMMANDS],
            allowed_commands=[],  # Empty = all allowed
        )
        
        with patch("jupiter.core.runner.run_command") as mock_run:
            with patch("jupiter.core.state.load_last_root", return_value=Path(".")):
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                runner.run(["anything", "goes"])
                mock_run.assert_called_once()
    
    def test_run_python_constructs_command(self):
        """run_python should use sys.executable."""
        runner = SecureRunner(
            plugin_id="test",
            permissions=[Permission.RUN_COMMANDS],
        )
        
        with patch("jupiter.core.runner.run_command") as mock_run:
            with patch("jupiter.core.state.load_last_root", return_value=Path(".")):
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                runner.run_python("script.py", args=["--flag"])
                
                # Verify python executable was used
                call_args = mock_run.call_args[0][0]
                assert "python" in call_args[0].lower()
                assert "script.py" in call_args


# =============================================================================
# ConfigProxy Tests
# =============================================================================

class TestConfigProxy:
    """Tests for ConfigProxy class."""
    
    def test_returns_default_value(self):
        """Should return default if key not found."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={},
            global_config={},
            project_overrides={},
        )
        
        assert config.get("nonexistent", "default") == "default"
    
    def test_returns_from_defaults(self):
        """Should return value from defaults."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"key": "from_defaults"},
            global_config={},
            project_overrides={},
        )
        
        assert config.get("key") == "from_defaults"
    
    def test_global_overrides_defaults(self):
        """Global config should override defaults."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"key": "from_defaults"},
            global_config={"key": "from_global"},
            project_overrides={},
        )
        
        assert config.get("key") == "from_global"
    
    def test_project_overrides_all(self):
        """Project overrides should override everything."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"key": "from_defaults"},
            global_config={"key": "from_global"},
            project_overrides={"key": "from_project"},
        )
        
        assert config.get("key") == "from_project"
    
    def test_supports_dot_notation(self):
        """Should support nested key access via dot notation."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"nested": {"deep": {"value": 42}}},
            global_config={},
            project_overrides={},
        )
        
        assert config.get("nested.deep.value") == 42
    
    def test_dot_notation_returns_default_on_missing(self):
        """Dot notation should return default if path doesn't exist."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={},
            global_config={},
            project_overrides={},
        )
        
        assert config.get("a.b.c", "missing") == "missing"
    
    def test_get_all_returns_merged(self):
        """get_all should return all merged values."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"a": 1, "b": 2},
            global_config={"b": 3, "c": 4},
            project_overrides={"c": 5},
        )
        
        all_config = config.get_all()
        assert all_config["a"] == 1
        assert all_config["b"] == 3
        assert all_config["c"] == 5
    
    def test_has_returns_true_for_existing(self):
        """has should return True for existing keys."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"key": "value"},
            global_config={},
            project_overrides={},
        )
        
        assert config.has("key") is True
        assert config.has("nonexistent") is False
    
    def test_dict_style_access(self):
        """Should support dict-style bracket access."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"key": "value"},
            global_config={},
            project_overrides={},
        )
        
        assert config["key"] == "value"
        
        with pytest.raises(KeyError):
            _ = config["nonexistent"]
    
    def test_contains_operator(self):
        """Should support 'in' operator."""
        config = ConfigProxy(
            plugin_id="test",
            defaults={"key": "value"},
            global_config={},
            project_overrides={},
        )
        
        assert "key" in config
        assert "nonexistent" not in config


# =============================================================================
# ServiceLocator Tests
# =============================================================================

class TestServiceLocator:
    """Tests for ServiceLocator class."""
    
    @pytest.fixture
    def mock_bridge(self):
        """Create a mock Bridge instance."""
        bridge = MagicMock()
        bridge.get_event_bus_proxy.return_value = MagicMock()
        return bridge
    
    def test_exposes_plugin_id(self, mock_bridge):
        """Should expose the plugin ID."""
        locator = ServiceLocator(
            plugin_id="test_plugin",
            bridge=mock_bridge,
            permissions=[],
            config_defaults={},
        )
        
        assert locator.plugin_id == "test_plugin"
    
    def test_exposes_permissions_copy(self, mock_bridge):
        """permissions should return a copy."""
        perms = [Permission.FS_READ, Permission.FS_WRITE]
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=perms,
            config_defaults={},
        )
        
        result = locator.permissions
        assert result == perms
        # Should be a copy
        result.append(Permission.RUN_COMMANDS)
        assert locator.permissions == perms  # Original unchanged
    
    def test_get_logger_returns_plugin_logger(self, mock_bridge):
        """get_logger should return a PluginLogger."""
        locator = ServiceLocator(
            plugin_id="test_plugin",
            bridge=mock_bridge,
            permissions=[],
            config_defaults={},
        )
        
        logger = locator.get_logger()
        assert isinstance(logger, PluginLogger)
        assert logger.plugin_id == "test_plugin"
    
    def test_get_logger_caches_instance(self, mock_bridge):
        """get_logger should return same instance."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[],
            config_defaults={},
        )
        
        logger1 = locator.get_logger()
        logger2 = locator.get_logger()
        assert logger1 is logger2
    
    def test_get_runner_returns_secure_runner(self, mock_bridge):
        """get_runner should return a SecureRunner."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[Permission.RUN_COMMANDS],
            config_defaults={},
        )
        
        with patch("jupiter.config.config.load_global_config") as mock_config:
            mock_config.return_value = MagicMock(security=None)
            runner = locator.get_runner()
            assert isinstance(runner, SecureRunner)
    
    def test_get_config_returns_config_proxy(self, mock_bridge):
        """get_config should return a ConfigProxy."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[],
            config_defaults={"default_key": "default_value"},
        )
        
        config = locator.get_config()
        assert isinstance(config, ConfigProxy)
        assert config.get("default_key") == "default_value"
    
    def test_get_history_requires_fs_read(self, mock_bridge):
        """get_history should require fs_read permission."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[],  # No permissions
            config_defaults={},
        )
        
        with pytest.raises(PermissionDeniedError):
            locator.get_history()
    
    def test_get_history_with_permission(self, mock_bridge):
        """get_history should work with fs_read permission."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[Permission.FS_READ],
            config_defaults={},
        )
        
        with patch("jupiter.core.state.load_last_root", return_value=Path(".")):
            history = locator.get_history()
            # Should return a HistoryManager
            assert hasattr(history, "project_root")
    
    def test_get_event_bus_returns_proxy(self, mock_bridge):
        """get_event_bus should return an EventBusProxy."""
        locator = ServiceLocator(
            plugin_id="my_plugin",
            bridge=mock_bridge,
            permissions=[],
            config_defaults={},
        )
        
        bus = locator.get_event_bus()
        # Should return an EventBusProxy instance
        assert hasattr(bus, "emit")
        assert hasattr(bus, "subscribe")
        assert hasattr(bus, "unsubscribe")
    
    def test_has_permission_returns_correct_result(self, mock_bridge):
        """has_permission should check permission list."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[Permission.FS_READ, Permission.FS_WRITE],
            config_defaults={},
        )
        
        assert locator.has_permission(Permission.FS_READ) is True
        assert locator.has_permission(Permission.FS_WRITE) is True
        assert locator.has_permission(Permission.RUN_COMMANDS) is False
    
    def test_require_permission_passes_when_granted(self, mock_bridge):
        """require_permission should pass when permission granted."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[Permission.FS_READ],
            config_defaults={},
        )
        
        # Should not raise
        locator.require_permission(Permission.FS_READ)
    
    def test_require_permission_raises_when_denied(self, mock_bridge):
        """require_permission should raise when permission missing."""
        locator = ServiceLocator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[],
            config_defaults={},
        )
        
        with pytest.raises(PermissionDeniedError):
            locator.require_permission(Permission.RUN_COMMANDS)


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestCreateServiceLocator:
    """Tests for create_service_locator factory function."""
    
    def test_creates_service_locator(self):
        """Factory should create ServiceLocator."""
        mock_bridge = MagicMock()
        
        locator = create_service_locator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[Permission.FS_READ],
            config_defaults={"key": "value"},
        )
        
        assert isinstance(locator, ServiceLocator)
        assert locator.plugin_id == "test"
    
    def test_defaults_to_empty_config(self):
        """Factory should default config_defaults to empty dict."""
        mock_bridge = MagicMock()
        
        locator = create_service_locator(
            plugin_id="test",
            bridge=mock_bridge,
            permissions=[],
        )
        
        config = locator.get_config()
        assert config.get_all() == {}
