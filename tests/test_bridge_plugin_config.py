"""Tests for jupiter.core.bridge.plugin_config module.

Version: 0.1.0

Tests for plugin configuration management with project overrides.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch
import yaml


# =============================================================================
# PluginConfigManager Tests
# =============================================================================

class TestPluginConfigManagerInit:
    """Tests for PluginConfigManager initialization."""
    
    def test_init_with_defaults(self):
        """Should initialize with provided defaults."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        defaults = {"key": "value", "nested": {"a": 1}}
        manager = PluginConfigManager("test_plugin", defaults=defaults)
        
        assert manager.plugin_id == "test_plugin"
        assert manager._defaults == defaults
    
    def test_init_without_defaults(self):
        """Should initialize with empty defaults."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        manager = PluginConfigManager("test_plugin")
        
        assert manager._defaults == {}
    
    def test_init_with_custom_plugins_dir(self, tmp_path):
        """Should use custom plugins directory."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        manager = PluginConfigManager("test_plugin", plugins_dir=tmp_path)
        
        assert manager._plugins_dir == tmp_path


class TestPluginConfigManagerGlobalConfig:
    """Tests for global config loading/saving."""
    
    def test_get_global_config_no_file(self, tmp_path):
        """Should return empty dict when no config file."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        manager = PluginConfigManager("test_plugin", plugins_dir=tmp_path)
        config = manager.get_global_config()
        
        assert config == {}
    
    def test_get_global_config_with_file(self, tmp_path):
        """Should load config from file."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        # Create config file
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        config_file = plugin_dir / "config.yaml"
        config_file.write_text("key: value\nnested:\n  a: 1")
        
        manager = PluginConfigManager("test_plugin", plugins_dir=tmp_path)
        config = manager.get_global_config()
        
        assert config == {"key": "value", "nested": {"a": 1}}
    
    def test_get_global_config_cached(self, tmp_path):
        """Should cache global config."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        # Create config file
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        config_file = plugin_dir / "config.yaml"
        config_file.write_text("key: value1")
        
        manager = PluginConfigManager("test_plugin", plugins_dir=tmp_path)
        config1 = manager.get_global_config()
        
        # Modify file
        config_file.write_text("key: value2")
        config2 = manager.get_global_config()
        
        assert config1 == config2  # Should be cached
    
    def test_get_global_config_reload(self, tmp_path):
        """Should reload config when requested."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        # Create config file
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        config_file = plugin_dir / "config.yaml"
        config_file.write_text("key: value1")
        
        manager = PluginConfigManager("test_plugin", plugins_dir=tmp_path)
        config1 = manager.get_global_config()
        
        # Modify file
        config_file.write_text("key: value2")
        config2 = manager.get_global_config(reload=True)
        
        assert config1["key"] == "value1"
        assert config2["key"] == "value2"
    
    def test_save_global_config(self, tmp_path):
        """Should save global config to file."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        manager = PluginConfigManager("test_plugin", plugins_dir=tmp_path)
        
        result = manager.save_global_config({"key": "saved", "num": 42})
        
        assert result is True
        
        config_file = tmp_path / "test_plugin" / "config.yaml"
        assert config_file.exists()
        
        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved == {"key": "saved", "num": 42}


class TestPluginConfigManagerProjectConfig:
    """Tests for project-specific config loading."""
    
    def test_get_project_config_no_project(self):
        """Should return empty dict when no project."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        with patch.object(PluginConfigManager, '_get_current_project_root', return_value=None):
            manager = PluginConfigManager("test_plugin")
            config = manager.get_project_config()
            
            assert config == {}
    
    def test_get_project_config_with_settings(self, tmp_path):
        """Should load project config from plugins.settings."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        # Create mock config
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {
            "test_plugin": {"key": "project_value", "enabled": True}
        }
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.core.bridge.plugin_config.PluginConfigManager._get_current_project_root', return_value=tmp_path):
            with patch('jupiter.config.config.load_config', return_value=mock_config):
                manager = PluginConfigManager("test_plugin")
                config = manager.get_project_config(tmp_path)
                
                assert config == {"key": "project_value", "enabled": True}
    
    def test_get_project_overrides(self, tmp_path):
        """Should extract config_overrides from project config."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {
            "test_plugin": {
                "enabled": True,
                "config_overrides": {"api_key": "xxx", "timeout": 30}
            }
        }
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin")
            overrides = manager.get_project_overrides(tmp_path)
            
            assert overrides == {"api_key": "xxx", "timeout": 30}


class TestPluginConfigManagerEnabledState:
    """Tests for plugin enabled/disabled state."""
    
    def test_is_enabled_no_project(self):
        """Should return True when no project (default enabled)."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        with patch.object(PluginConfigManager, '_get_current_project_root', return_value=None):
            manager = PluginConfigManager("test_plugin")
            
            assert manager.is_enabled_for_project() is True
    
    def test_is_enabled_explicit_true(self, tmp_path):
        """Should respect explicit enabled: true."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {"test_plugin": {"enabled": True}}
        mock_plugins_config.disabled = []
        mock_plugins_config.enabled = []
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin")
            
            assert manager.is_enabled_for_project(tmp_path) is True
    
    def test_is_enabled_explicit_false(self, tmp_path):
        """Should respect explicit enabled: false."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {"test_plugin": {"enabled": False}}
        mock_plugins_config.disabled = []
        mock_plugins_config.enabled = []
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin")
            
            assert manager.is_enabled_for_project(tmp_path) is False
    
    def test_is_enabled_in_disabled_list(self, tmp_path):
        """Should return False when in disabled list."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {}
        mock_plugins_config.disabled = ["test_plugin", "other_plugin"]
        mock_plugins_config.enabled = []
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin")
            
            assert manager.is_enabled_for_project(tmp_path) is False
    
    def test_is_enabled_not_in_whitelist(self, tmp_path):
        """Should return False when not in enabled whitelist."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {}
        mock_plugins_config.disabled = []
        mock_plugins_config.enabled = ["other_plugin"]  # Whitelist without test_plugin
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin")
            
            assert manager.is_enabled_for_project(tmp_path) is False
    
    def test_is_enabled_in_whitelist(self, tmp_path):
        """Should return True when in enabled whitelist."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {}
        mock_plugins_config.disabled = []
        mock_plugins_config.enabled = ["test_plugin", "other_plugin"]
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin")
            
            assert manager.is_enabled_for_project(tmp_path) is True


class TestPluginConfigManagerMergedConfig:
    """Tests for merged configuration."""
    
    def test_get_merged_config_defaults_only(self):
        """Should return defaults when no other config."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        defaults = {"key": "default", "num": 10}
        
        with patch.object(PluginConfigManager, '_get_current_project_root', return_value=None):
            manager = PluginConfigManager("test_plugin", defaults=defaults)
            manager._plugins_dir = Path("/nonexistent")
            
            config = manager.get_merged_config()
            
            assert config == {"key": "default", "num": 10}
    
    def test_get_merged_config_global_overrides_defaults(self, tmp_path):
        """Global config should override defaults."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        defaults = {"key": "default", "num": 10}
        
        # Create global config
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "config.yaml").write_text("key: global\nextra: added")
        
        with patch.object(PluginConfigManager, '_get_current_project_root', return_value=None):
            manager = PluginConfigManager("test_plugin", defaults=defaults, plugins_dir=tmp_path)
            
            config = manager.get_merged_config()
            
            assert config["key"] == "global"  # Overridden
            assert config["num"] == 10  # From defaults
            assert config["extra"] == "added"  # Added
    
    def test_get_merged_config_project_overrides_all(self, tmp_path):
        """Project overrides should override everything."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        defaults = {"key": "default", "num": 10}
        
        # Create global config
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "config.yaml").write_text("key: global\nextra: added")
        
        # Mock project overrides
        mock_plugins_config = MagicMock()
        mock_plugins_config.settings = {
            "test_plugin": {
                "config_overrides": {"key": "project", "num": 99}
            }
        }
        
        mock_config = MagicMock()
        mock_config.plugins = mock_plugins_config
        
        with patch('jupiter.config.config.load_config', return_value=mock_config):
            manager = PluginConfigManager("test_plugin", defaults=defaults, plugins_dir=tmp_path)
            
            config = manager.get_merged_config(tmp_path)
            
            assert config["key"] == "project"  # Project override
            assert config["num"] == 99  # Project override
            assert config["extra"] == "added"  # From global
    
    def test_deep_merge_nested(self):
        """Should deep merge nested dictionaries."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        base = {
            "a": 1,
            "nested": {
                "x": 10,
                "y": 20
            }
        }
        override = {
            "nested": {
                "y": 200,
                "z": 300
            }
        }
        
        result = PluginConfigManager._deep_merge(base, override)
        
        assert result["a"] == 1
        assert result["nested"]["x"] == 10
        assert result["nested"]["y"] == 200
        assert result["nested"]["z"] == 300
    
    def test_get_nested_value(self):
        """Should get nested value with dot notation."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        data = {
            "a": {
                "b": {
                    "c": "value"
                }
            }
        }
        
        assert PluginConfigManager._get_nested(data, "a.b.c") == "value"
        assert PluginConfigManager._get_nested(data, "a.b") == {"c": "value"}
        assert PluginConfigManager._get_nested(data, "a.x", "default") == "default"
    
    def test_get_method(self, tmp_path):
        """Should get specific config value."""
        from jupiter.core.bridge.plugin_config import PluginConfigManager
        
        defaults = {"key": "value", "nested": {"a": 1}}
        
        with patch.object(PluginConfigManager, '_get_current_project_root', return_value=None):
            manager = PluginConfigManager("test_plugin", defaults=defaults)
            manager._plugins_dir = Path("/nonexistent")
            
            assert manager.get("key") == "value"
            assert manager.get("nested.a") == 1
            assert manager.get("missing", "default") == "default"


# =============================================================================
# ProjectPluginRegistry Tests
# =============================================================================

class TestProjectPluginRegistry:
    """Tests for ProjectPluginRegistry."""
    
    def test_is_enabled_caches(self):
        """Should cache enabled state."""
        from jupiter.core.bridge.plugin_config import ProjectPluginRegistry, PluginConfigManager
        
        registry = ProjectPluginRegistry()
        
        with patch.object(PluginConfigManager, 'is_enabled_for_project', return_value=True) as mock:
            result1 = registry.is_enabled("test_plugin")
            result2 = registry.is_enabled("test_plugin")
            
            assert result1 is True
            assert result2 is True
            assert mock.call_count == 1  # Only called once
    
    def test_get_enabled_plugins(self):
        """Should filter enabled plugins."""
        from jupiter.core.bridge.plugin_config import ProjectPluginRegistry, PluginConfigManager
        
        registry = ProjectPluginRegistry()
        
        # Set cache directly for testing (no need for mock_enabled)
        registry._cache = {
            "plugin1": True,
            "plugin2": False,
            "plugin3": True,
        }
        
        all_plugins = ["plugin1", "plugin2", "plugin3"]
        enabled = registry.get_enabled_plugins(all_plugins)
        
        assert enabled == ["plugin1", "plugin3"]
    
    def test_get_disabled_plugins(self):
        """Should filter disabled plugins."""
        from jupiter.core.bridge.plugin_config import ProjectPluginRegistry
        
        registry = ProjectPluginRegistry()
        registry._cache = {
            "plugin1": True,
            "plugin2": False,
            "plugin3": True,
        }
        
        all_plugins = ["plugin1", "plugin2", "plugin3"]
        disabled = registry.get_disabled_plugins(all_plugins)
        
        assert disabled == ["plugin2"]
    
    def test_clear_cache(self):
        """Should clear the cache."""
        from jupiter.core.bridge.plugin_config import ProjectPluginRegistry
        
        registry = ProjectPluginRegistry()
        registry._cache = {"plugin1": True}
        
        registry.clear_cache()
        
        assert registry._cache == {}
