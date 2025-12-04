"""
Tests for jupiter.core.bridge.governance module.

Version: 0.1.0

Tests for governance features including whitelist/blacklist,
feature flags, and policy management.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock

pytestmark = pytest.mark.anyio

from jupiter.core.bridge.governance import (
    ListMode,
    PolicyAction,
    FeatureFlag,
    PluginPolicy,
    GovernanceConfig,
    PolicyCheckResult,
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


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager():
    """Create a fresh governance manager."""
    return GovernanceManager()


@pytest.fixture
def whitelist_manager():
    """Create a manager in whitelist mode."""
    config = GovernanceConfig(
        mode=ListMode.WHITELIST,
        whitelist={"allowed_plugin", "another_allowed"},
    )
    return GovernanceManager(config=config)


@pytest.fixture
def blacklist_manager():
    """Create a manager in blacklist mode."""
    config = GovernanceConfig(
        mode=ListMode.BLACKLIST,
        blacklist={"banned_plugin", "another_banned"},
    )
    return GovernanceManager(config=config)


@pytest.fixture(autouse=True)
def reset_global():
    """Reset global governance manager before and after each test."""
    reset_governance()
    yield
    reset_governance()


# =============================================================================
# ListMode Tests
# =============================================================================

class TestListMode:
    """Tests for ListMode enum."""

    def test_values(self):
        """Test enum values."""
        assert ListMode.DISABLED.value == "disabled"
        assert ListMode.WHITELIST.value == "whitelist"
        assert ListMode.BLACKLIST.value == "blacklist"


# =============================================================================
# PolicyAction Tests
# =============================================================================

class TestPolicyAction:
    """Tests for PolicyAction enum."""

    def test_values(self):
        """Test enum values."""
        assert PolicyAction.ALLOW.value == "allow"
        assert PolicyAction.BLOCK.value == "block"
        assert PolicyAction.WARN.value == "warn"


# =============================================================================
# FeatureFlag Tests
# =============================================================================

class TestFeatureFlag:
    """Tests for FeatureFlag dataclass."""

    def test_defaults(self):
        """Test default values."""
        flag = FeatureFlag(name="test_feature")
        
        assert flag.name == "test_feature"
        assert flag.enabled is True
        assert flag.description == ""
        assert flag.requires_dev_mode is False
        assert flag.requires_permissions == []
        assert flag.deprecated is False

    def test_custom_values(self):
        """Test custom values."""
        flag = FeatureFlag(
            name="experimental",
            enabled=False,
            description="An experimental feature",
            requires_dev_mode=True,
            requires_permissions=["fs_read"],
            deprecated=True,
            deprecation_message="Use new_feature instead",
        )
        
        assert flag.name == "experimental"
        assert flag.enabled is False
        assert flag.requires_dev_mode is True
        assert flag.deprecated is True

    def test_to_dict(self):
        """Test serialization."""
        flag = FeatureFlag(name="test", enabled=True)
        data = flag.to_dict()
        
        assert data["name"] == "test"
        assert data["enabled"] is True

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "name": "test",
            "enabled": False,
            "requires_dev_mode": True,
        }
        flag = FeatureFlag.from_dict(data)
        
        assert flag.name == "test"
        assert flag.enabled is False
        assert flag.requires_dev_mode is True


# =============================================================================
# PluginPolicy Tests
# =============================================================================

class TestPluginPolicy:
    """Tests for PluginPolicy dataclass."""

    def test_defaults(self):
        """Test default values."""
        policy = PluginPolicy(plugin_id="test_plugin")
        
        assert policy.plugin_id == "test_plugin"
        assert policy.allowed is True
        assert policy.reason == ""
        assert policy.feature_flags == {}
        assert policy.max_jobs is None

    def test_to_dict(self):
        """Test serialization."""
        policy = PluginPolicy(
            plugin_id="test",
            allowed=False,
            reason="Security concern",
        )
        data = policy.to_dict()
        
        assert data["plugin_id"] == "test"
        assert data["allowed"] is False
        assert data["reason"] == "Security concern"

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "plugin_id": "test",
            "allowed": False,
            "feature_flags": {
                "feature1": {"name": "feature1", "enabled": True},
                "feature2": False,  # Short form
            },
        }
        policy = PluginPolicy.from_dict(data)
        
        assert policy.plugin_id == "test"
        assert policy.allowed is False
        assert "feature1" in policy.feature_flags
        assert "feature2" in policy.feature_flags


# =============================================================================
# GovernanceConfig Tests
# =============================================================================

class TestGovernanceConfig:
    """Tests for GovernanceConfig dataclass."""

    def test_defaults(self):
        """Test default values."""
        config = GovernanceConfig()
        
        assert config.mode == ListMode.DISABLED
        assert config.whitelist == set()
        assert config.blacklist == set()
        assert config.default_action == PolicyAction.BLOCK

    def test_to_dict(self):
        """Test serialization."""
        config = GovernanceConfig(
            mode=ListMode.WHITELIST,
            whitelist={"plugin1", "plugin2"},
        )
        data = config.to_dict()
        
        assert data["mode"] == "whitelist"
        assert set(data["whitelist"]) == {"plugin1", "plugin2"}

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "mode": "blacklist",
            "blacklist": ["bad_plugin"],
            "default_action": "warn",
        }
        config = GovernanceConfig.from_dict(data)
        
        assert config.mode == ListMode.BLACKLIST
        assert "bad_plugin" in config.blacklist
        assert config.default_action == PolicyAction.WARN

    def test_from_dict_invalid_mode(self):
        """Test deserialization with invalid mode."""
        data = {"mode": "invalid"}
        config = GovernanceConfig.from_dict(data)
        
        assert config.mode == ListMode.DISABLED


# =============================================================================
# PolicyCheckResult Tests
# =============================================================================

class TestPolicyCheckResult:
    """Tests for PolicyCheckResult dataclass."""

    def test_creation(self):
        """Test creating a result."""
        result = PolicyCheckResult(
            allowed=False,
            action=PolicyAction.BLOCK,
            reason="Not in whitelist",
            plugin_id="test",
            policy_type="whitelist",
        )
        
        assert result.allowed is False
        assert result.action == PolicyAction.BLOCK
        assert result.reason == "Not in whitelist"

    def test_to_dict(self):
        """Test serialization."""
        result = PolicyCheckResult(
            allowed=True,
            action=PolicyAction.ALLOW,
            plugin_id="test",
        )
        data = result.to_dict()
        
        assert data["allowed"] is True
        assert data["action"] == "allow"


# =============================================================================
# GovernanceManager Basic Tests
# =============================================================================

class TestGovernanceManagerBasic:
    """Basic tests for GovernanceManager."""

    def test_initialization(self, manager):
        """Test manager initialization."""
        assert manager.mode == ListMode.DISABLED
        assert manager.config is not None

    def test_set_mode(self, manager):
        """Test setting list mode."""
        manager.set_mode(ListMode.WHITELIST)
        
        assert manager.mode == ListMode.WHITELIST

    def test_config_property(self, manager):
        """Test config property."""
        config = manager.config
        
        assert isinstance(config, GovernanceConfig)


# =============================================================================
# Whitelist Tests
# =============================================================================

class TestWhitelist:
    """Tests for whitelist functionality."""

    def test_add_to_whitelist(self, manager):
        """Test adding to whitelist."""
        result = manager.add_to_whitelist("new_plugin")
        
        assert result is True
        assert "new_plugin" in manager.get_whitelist()

    def test_add_duplicate_to_whitelist(self, manager):
        """Test adding duplicate to whitelist."""
        manager.add_to_whitelist("plugin")
        result = manager.add_to_whitelist("plugin")
        
        assert result is False

    def test_remove_from_whitelist(self, manager):
        """Test removing from whitelist."""
        manager.add_to_whitelist("plugin")
        result = manager.remove_from_whitelist("plugin")
        
        assert result is True
        assert "plugin" not in manager.get_whitelist()

    def test_remove_nonexistent_from_whitelist(self, manager):
        """Test removing non-existent from whitelist."""
        result = manager.remove_from_whitelist("nonexistent")
        
        assert result is False

    def test_whitelist_mode_allowed(self, whitelist_manager):
        """Test allowed plugin in whitelist mode."""
        result = whitelist_manager.is_plugin_allowed("allowed_plugin")
        
        assert result is True

    def test_whitelist_mode_blocked(self, whitelist_manager):
        """Test blocked plugin in whitelist mode."""
        result = whitelist_manager.is_plugin_allowed("not_in_whitelist")
        
        assert result is False

    def test_whitelist_check_details(self, whitelist_manager):
        """Test check with details in whitelist mode."""
        result = whitelist_manager.check_plugin_allowed("not_in_whitelist")
        
        assert result.allowed is False
        assert result.policy_type == "whitelist"
        assert "not in whitelist" in result.reason


# =============================================================================
# Blacklist Tests
# =============================================================================

class TestBlacklist:
    """Tests for blacklist functionality."""

    def test_add_to_blacklist(self, manager):
        """Test adding to blacklist."""
        result = manager.add_to_blacklist("bad_plugin", "Security issue")
        
        assert result is True
        assert "bad_plugin" in manager.get_blacklist()

    def test_add_duplicate_to_blacklist(self, manager):
        """Test adding duplicate to blacklist."""
        manager.add_to_blacklist("plugin")
        result = manager.add_to_blacklist("plugin")
        
        assert result is False

    def test_remove_from_blacklist(self, manager):
        """Test removing from blacklist."""
        manager.add_to_blacklist("plugin")
        result = manager.remove_from_blacklist("plugin")
        
        assert result is True
        assert "plugin" not in manager.get_blacklist()

    def test_blacklist_mode_allowed(self, blacklist_manager):
        """Test allowed plugin in blacklist mode."""
        result = blacklist_manager.is_plugin_allowed("good_plugin")
        
        assert result is True

    def test_blacklist_mode_blocked(self, blacklist_manager):
        """Test blocked plugin in blacklist mode."""
        result = blacklist_manager.is_plugin_allowed("banned_plugin")
        
        assert result is False

    def test_blacklist_check_details(self, blacklist_manager):
        """Test check with details in blacklist mode."""
        result = blacklist_manager.check_plugin_allowed("banned_plugin")
        
        assert result.allowed is False
        assert result.policy_type == "blacklist"

    def test_blacklist_with_reason(self, manager):
        """Test blacklist with custom reason."""
        manager.set_mode(ListMode.BLACKLIST)
        manager.add_to_blacklist("bad_plugin", "Known vulnerability CVE-2025-1234")
        
        result = manager.check_plugin_allowed("bad_plugin")
        
        assert "CVE-2025-1234" in result.reason


# =============================================================================
# Disabled Mode Tests
# =============================================================================

class TestDisabledMode:
    """Tests for disabled mode."""

    def test_disabled_mode_allows_all(self, manager):
        """Test that disabled mode allows all plugins."""
        assert manager.is_plugin_allowed("any_plugin") is True
        assert manager.is_plugin_allowed("another_plugin") is True

    def test_disabled_mode_check_details(self, manager):
        """Test check details in disabled mode."""
        result = manager.check_plugin_allowed("any_plugin")
        
        assert result.allowed is True
        assert result.policy_type == "disabled"


# =============================================================================
# Feature Flags Tests
# =============================================================================

class TestFeatureFlags:
    """Tests for feature flags."""

    def test_default_feature_enabled(self, manager):
        """Test that unknown features are enabled by default."""
        result = manager.is_feature_enabled("plugin", "unknown_feature")
        
        assert result is True

    def test_set_feature_flag(self, manager):
        """Test setting a feature flag."""
        manager.set_feature_flag("plugin", "feature1", enabled=False)
        
        result = manager.is_feature_enabled("plugin", "feature1")
        
        assert result is False

    def test_set_feature_flag_with_description(self, manager):
        """Test setting a feature flag with description."""
        manager.set_feature_flag(
            "plugin",
            "experimental",
            enabled=True,
            description="An experimental feature",
            requires_dev_mode=True,
        )
        
        flags = manager.get_feature_flags("plugin")
        
        assert "experimental" in flags
        assert flags["experimental"].description == "An experimental feature"
        assert flags["experimental"].requires_dev_mode is True

    def test_remove_feature_flag(self, manager):
        """Test removing a feature flag."""
        manager.set_feature_flag("plugin", "feature1", enabled=False)
        
        result = manager.remove_feature_flag("plugin", "feature1")
        
        assert result is True
        assert manager.is_feature_enabled("plugin", "feature1") is True  # Back to default

    def test_remove_nonexistent_feature_flag(self, manager):
        """Test removing non-existent feature flag."""
        result = manager.remove_feature_flag("plugin", "nonexistent")
        
        assert result is False

    def test_feature_requires_dev_mode(self, manager):
        """Test feature that requires dev mode."""
        manager.set_feature_flag(
            "plugin",
            "dev_feature",
            enabled=True,
            requires_dev_mode=True,
        )
        
        # Without dev mode
        assert manager.is_feature_enabled("plugin", "dev_feature", dev_mode=False) is False
        
        # With dev mode
        assert manager.is_feature_enabled("plugin", "dev_feature", dev_mode=True) is True

    def test_get_feature_flags_empty(self, manager):
        """Test getting flags for plugin with no flags."""
        flags = manager.get_feature_flags("unknown_plugin")
        
        assert flags == {}

    def test_global_feature_flag(self, manager):
        """Test global feature flags."""
        manager.set_global_feature_flag("global_feature", False)
        
        # Should be disabled for all plugins
        assert manager.is_feature_enabled("plugin1", "global_feature") is False
        assert manager.is_feature_enabled("plugin2", "global_feature") is False

    def test_get_global_feature_flags(self, manager):
        """Test getting global flags."""
        manager.set_global_feature_flag("flag1", True)
        manager.set_global_feature_flag("flag2", False)
        
        flags = manager.get_global_feature_flags()
        
        assert flags["flag1"] is True
        assert flags["flag2"] is False


# =============================================================================
# Plugin Policy Tests
# =============================================================================

class TestPluginPolicies:
    """Tests for plugin policies."""

    def test_set_plugin_policy(self, manager):
        """Test setting a plugin policy."""
        policy = PluginPolicy(
            plugin_id="test_plugin",
            allowed=False,
            reason="Deprecated",
        )
        
        manager.set_plugin_policy(policy)
        
        retrieved = manager.get_plugin_policy("test_plugin")
        assert retrieved is not None
        assert retrieved.allowed is False
        assert retrieved.reason == "Deprecated"

    def test_get_nonexistent_policy(self, manager):
        """Test getting non-existent policy."""
        policy = manager.get_plugin_policy("nonexistent")
        
        assert policy is None

    def test_remove_plugin_policy(self, manager):
        """Test removing a plugin policy."""
        policy = PluginPolicy(plugin_id="test")
        manager.set_plugin_policy(policy)
        
        result = manager.remove_plugin_policy("test")
        
        assert result is True
        assert manager.get_plugin_policy("test") is None

    def test_get_all_policies(self, manager):
        """Test getting all policies."""
        manager.set_plugin_policy(PluginPolicy(plugin_id="p1"))
        manager.set_plugin_policy(PluginPolicy(plugin_id="p2"))
        
        policies = manager.get_all_policies()
        
        assert "p1" in policies
        assert "p2" in policies


# =============================================================================
# Protected Plugins Tests
# =============================================================================

class TestProtectedPlugins:
    """Tests for protected plugins."""

    def test_add_protected_plugin(self, manager):
        """Test adding a protected plugin."""
        result = manager.add_protected_plugin("core_plugin")
        
        assert result is True
        assert manager.is_protected("core_plugin") is True

    def test_add_duplicate_protected(self, manager):
        """Test adding duplicate protected plugin."""
        manager.add_protected_plugin("plugin")
        result = manager.add_protected_plugin("plugin")
        
        assert result is False

    def test_remove_protected_plugin(self, manager):
        """Test removing protected status."""
        manager.add_protected_plugin("plugin")
        result = manager.remove_protected_plugin("plugin")
        
        assert result is True
        assert manager.is_protected("plugin") is False

    def test_cannot_blacklist_protected(self, manager):
        """Test that protected plugins cannot be blacklisted."""
        manager.add_protected_plugin("core_plugin")
        
        result = manager.add_to_blacklist("core_plugin")
        
        assert result is False
        assert "core_plugin" not in manager.get_blacklist()

    def test_get_protected_plugins(self, manager):
        """Test getting list of protected plugins."""
        manager.add_protected_plugin("p1")
        manager.add_protected_plugin("p2")
        
        protected = manager.get_protected_plugins()
        
        assert "p1" in protected
        assert "p2" in protected


# =============================================================================
# Violation Callbacks Tests
# =============================================================================

class TestViolationCallbacks:
    """Tests for violation callbacks."""

    def test_add_violation_callback(self, whitelist_manager):
        """Test adding a violation callback."""
        callback = Mock()
        whitelist_manager.add_violation_callback(callback)
        
        whitelist_manager.check_plugin_allowed("blocked_plugin")
        
        callback.assert_called_once()

    def test_remove_violation_callback(self, whitelist_manager):
        """Test removing a violation callback."""
        callback = Mock()
        whitelist_manager.add_violation_callback(callback)
        
        result = whitelist_manager.remove_violation_callback(callback)
        
        assert result is True
        
        whitelist_manager.check_plugin_allowed("blocked_plugin")
        callback.assert_not_called()

    def test_callback_receives_result(self, whitelist_manager):
        """Test that callback receives PolicyCheckResult."""
        received = []
        
        def callback(result):
            received.append(result)
        
        whitelist_manager.add_violation_callback(callback)
        whitelist_manager.check_plugin_allowed("blocked_plugin")
        
        assert len(received) == 1
        assert isinstance(received[0], PolicyCheckResult)
        assert received[0].allowed is False


# =============================================================================
# Persistence Tests
# =============================================================================

class TestPersistence:
    """Tests for configuration persistence."""

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "governance.json"
            
            # Create and save
            manager1 = GovernanceManager(config_path=config_path)
            manager1.set_mode(ListMode.WHITELIST)
            manager1.add_to_whitelist("plugin1")
            manager1.set_feature_flag("plugin1", "feature1", enabled=False)
            
            # Load in new manager
            manager2 = GovernanceManager(config_path=config_path)
            
            assert manager2.mode == ListMode.WHITELIST
            assert "plugin1" in manager2.get_whitelist()
            assert manager2.is_feature_enabled("plugin1", "feature1") is False

    def test_reload_config(self):
        """Test reloading configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "governance.json"
            
            manager = GovernanceManager(config_path=config_path)
            manager.set_mode(ListMode.BLACKLIST)
            
            # Manually modify file
            with open(config_path, "r") as f:
                data = json.load(f)
            data["mode"] = "whitelist"
            with open(config_path, "w") as f:
                json.dump(data, f)
            
            # Reload
            manager.reload_config()
            
            assert manager.mode == ListMode.WHITELIST


# =============================================================================
# Stats and Status Tests
# =============================================================================

class TestStatsStatus:
    """Tests for statistics and status."""

    def test_get_stats(self, manager):
        """Test getting statistics."""
        manager.add_to_whitelist("p1")
        manager.add_to_blacklist("p2")
        
        stats = manager.get_stats()
        
        assert stats["whitelist_count"] == 1
        assert stats["blacklist_count"] == 1
        assert "checks_performed" in stats

    def test_get_status(self, manager):
        """Test getting status."""
        manager.set_mode(ListMode.WHITELIST)
        manager.add_to_whitelist("plugin1")
        
        status = manager.get_status()
        
        assert status["mode"] == "whitelist"
        assert "plugin1" in status["whitelist"]

    def test_stats_track_violations(self, whitelist_manager):
        """Test that stats track violations."""
        whitelist_manager.check_plugin_allowed("blocked1")
        whitelist_manager.check_plugin_allowed("blocked2")
        
        stats = whitelist_manager.get_stats()
        
        assert stats["violations_blocked"] == 2

    def test_update_config(self, manager):
        """Test updating entire configuration."""
        new_config = GovernanceConfig(
            mode=ListMode.BLACKLIST,
            blacklist={"bad_plugin"},
        )
        
        manager.update_config(new_config)
        
        assert manager.mode == ListMode.BLACKLIST
        assert "bad_plugin" in manager.get_blacklist()


# =============================================================================
# Global Functions Tests
# =============================================================================

class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_governance_singleton(self):
        """Test that get_governance returns singleton."""
        g1 = get_governance()
        g2 = get_governance()
        
        assert g1 is g2

    def test_init_governance(self):
        """Test initializing governance."""
        config = GovernanceConfig(mode=ListMode.WHITELIST)
        
        manager = init_governance(config=config)
        
        assert manager.mode == ListMode.WHITELIST

    def test_reset_governance(self):
        """Test resetting governance."""
        g1 = get_governance()
        g1.set_mode(ListMode.WHITELIST)
        
        reset_governance()
        
        g2 = get_governance()
        assert g1 is not g2
        assert g2.mode == ListMode.DISABLED

    def test_is_plugin_allowed_function(self):
        """Test is_plugin_allowed function."""
        result = is_plugin_allowed("any_plugin")
        
        assert result is True  # Disabled mode allows all

    def test_check_plugin_allowed_function(self):
        """Test check_plugin_allowed function."""
        result = check_plugin_allowed("any_plugin")
        
        assert isinstance(result, PolicyCheckResult)
        assert result.allowed is True

    def test_is_feature_enabled_function(self):
        """Test is_feature_enabled function."""
        set_feature_flag("plugin", "feature", enabled=False)
        
        assert is_feature_enabled("plugin", "feature") is False

    def test_add_to_whitelist_function(self):
        """Test add_to_whitelist function."""
        result = add_to_whitelist("my_plugin")
        
        assert result is True
        assert "my_plugin" in get_governance().get_whitelist()

    def test_add_to_blacklist_function(self):
        """Test add_to_blacklist function."""
        result = add_to_blacklist("bad_plugin", "Test reason")
        
        assert result is True
        assert "bad_plugin" in get_governance().get_blacklist()

    def test_get_governance_status_function(self):
        """Test get_governance_status function."""
        status = get_governance_status()
        
        assert "mode" in status
        assert "whitelist" in status


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for governance scenarios."""

    def test_full_whitelist_workflow(self):
        """Test complete whitelist workflow."""
        manager = GovernanceManager()
        
        # Set up whitelist
        manager.set_mode(ListMode.WHITELIST)
        manager.add_to_whitelist("trusted_plugin_1")
        manager.add_to_whitelist("trusted_plugin_2")
        
        # Check allowed
        assert manager.is_plugin_allowed("trusted_plugin_1") is True
        assert manager.is_plugin_allowed("trusted_plugin_2") is True
        
        # Check blocked
        assert manager.is_plugin_allowed("unknown_plugin") is False
        
        # Remove from whitelist
        manager.remove_from_whitelist("trusted_plugin_2")
        assert manager.is_plugin_allowed("trusted_plugin_2") is False

    def test_full_blacklist_workflow(self):
        """Test complete blacklist workflow."""
        manager = GovernanceManager()
        
        # Set up blacklist
        manager.set_mode(ListMode.BLACKLIST)
        manager.add_to_blacklist("malicious_plugin", "Contains malware")
        manager.add_to_blacklist("deprecated_plugin", "No longer maintained")
        
        # Check blocked
        assert manager.is_plugin_allowed("malicious_plugin") is False
        assert manager.is_plugin_allowed("deprecated_plugin") is False
        
        # Check allowed
        assert manager.is_plugin_allowed("good_plugin") is True
        
        # Rehabilitate a plugin
        manager.remove_from_blacklist("deprecated_plugin")
        assert manager.is_plugin_allowed("deprecated_plugin") is True

    def test_feature_flags_with_policies(self):
        """Test feature flags combined with policies."""
        manager = GovernanceManager()
        
        # Set up policy with feature flags
        policy = PluginPolicy(
            plugin_id="feature_plugin",
            feature_flags={
                "beta_ui": FeatureFlag(name="beta_ui", enabled=True),
                "experimental_api": FeatureFlag(
                    name="experimental_api",
                    enabled=True,
                    requires_dev_mode=True,
                ),
            },
        )
        manager.set_plugin_policy(policy)
        
        # Check features
        assert manager.is_feature_enabled("feature_plugin", "beta_ui") is True
        assert manager.is_feature_enabled("feature_plugin", "experimental_api", dev_mode=False) is False
        assert manager.is_feature_enabled("feature_plugin", "experimental_api", dev_mode=True) is True

    def test_protected_plugins_cannot_be_disabled(self):
        """Test that protected plugins stay enabled."""
        manager = GovernanceManager()
        
        # Protect core plugins
        manager.add_protected_plugin("settings_update")
        manager.add_protected_plugin("core_scanner")
        
        # Try to blacklist
        manager.set_mode(ListMode.BLACKLIST)
        result1 = manager.add_to_blacklist("settings_update")
        result2 = manager.add_to_blacklist("core_scanner")
        
        assert result1 is False
        assert result2 is False
        
        # They should still be allowed
        assert manager.is_plugin_allowed("settings_update") is True
        assert manager.is_plugin_allowed("core_scanner") is True

    def test_global_flags_override_plugin_flags(self):
        """Test that global flags take precedence."""
        manager = GovernanceManager()
        
        # Enable feature at plugin level
        manager.set_feature_flag("plugin", "feature1", enabled=True)
        
        # Disable globally
        manager.set_global_feature_flag("feature1", False)
        
        # Should be disabled
        assert manager.is_feature_enabled("plugin", "feature1") is False
