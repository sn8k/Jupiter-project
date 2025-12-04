"""Jupiter Plugin Bridge - Governance.

Version: 0.1.0

Provides governance controls for plugin management:
- Whitelist/blacklist for plugin installation and loading
- Feature flags for enabling/disabling features without uninstall
- Policy enforcement across the plugin system

Usage:
    from jupiter.core.bridge.governance import (
        get_governance,
        is_plugin_allowed,
        is_feature_enabled,
        add_to_whitelist,
        add_to_blacklist,
    )
    
    # Check if plugin is allowed
    if is_plugin_allowed("my_plugin"):
        # Load plugin
        pass
    
    # Check feature flag
    if is_feature_enabled("my_plugin", "experimental_feature"):
        # Use feature
        pass
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


# =============================================================================
# ENUMS
# =============================================================================

class ListMode(Enum):
    """Mode for whitelist/blacklist enforcement."""
    
    DISABLED = "disabled"  # No filtering
    WHITELIST = "whitelist"  # Only allow listed plugins
    BLACKLIST = "blacklist"  # Block listed plugins


class PolicyAction(Enum):
    """Action to take when policy is violated."""
    
    ALLOW = "allow"  # Allow despite violation (log warning)
    BLOCK = "block"  # Block the operation
    WARN = "warn"  # Allow but emit warning event


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class FeatureFlag:
    """A feature flag for a plugin."""
    
    name: str
    enabled: bool = True
    description: str = ""
    # Optional conditions
    requires_dev_mode: bool = False
    requires_permissions: List[str] = field(default_factory=list)
    # Metadata
    deprecated: bool = False
    deprecation_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "description": self.description,
            "requires_dev_mode": self.requires_dev_mode,
            "requires_permissions": self.requires_permissions,
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureFlag":
        """Create from dictionary."""
        return cls(
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            description=data.get("description", ""),
            requires_dev_mode=data.get("requires_dev_mode", False),
            requires_permissions=data.get("requires_permissions", []),
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message", ""),
        )


@dataclass
class PluginPolicy:
    """Policy configuration for a specific plugin."""
    
    plugin_id: str
    # Installation/loading
    allowed: bool = True
    reason: str = ""
    # Feature flags
    feature_flags: Dict[str, FeatureFlag] = field(default_factory=dict)
    # Restrictions
    max_jobs: Optional[int] = None
    rate_limit_override: Optional[int] = None
    # Metadata
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "plugin_id": self.plugin_id,
            "allowed": self.allowed,
            "reason": self.reason,
            "feature_flags": {
                k: v.to_dict() for k, v in self.feature_flags.items()
            },
            "max_jobs": self.max_jobs,
            "rate_limit_override": self.rate_limit_override,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginPolicy":
        """Create from dictionary."""
        feature_flags = {}
        for k, v in data.get("feature_flags", {}).items():
            if isinstance(v, dict):
                feature_flags[k] = FeatureFlag.from_dict(v)
            elif isinstance(v, bool):
                feature_flags[k] = FeatureFlag(name=k, enabled=v)
        
        return cls(
            plugin_id=data.get("plugin_id", ""),
            allowed=data.get("allowed", True),
            reason=data.get("reason", ""),
            feature_flags=feature_flags,
            max_jobs=data.get("max_jobs"),
            rate_limit_override=data.get("rate_limit_override"),
            notes=data.get("notes", ""),
        )


@dataclass
class GovernanceConfig:
    """Global governance configuration."""
    
    # List mode
    mode: ListMode = ListMode.DISABLED
    
    # Whitelist (only used if mode == WHITELIST)
    whitelist: Set[str] = field(default_factory=set)
    
    # Blacklist (only used if mode == BLACKLIST)
    blacklist: Set[str] = field(default_factory=set)
    
    # Default policy action
    default_action: PolicyAction = PolicyAction.BLOCK
    
    # Global feature flags (apply to all plugins)
    global_feature_flags: Dict[str, bool] = field(default_factory=dict)
    
    # Per-plugin policies
    plugin_policies: Dict[str, PluginPolicy] = field(default_factory=dict)
    
    # Protected plugins that cannot be disabled
    protected_plugins: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "mode": self.mode.value,
            "whitelist": list(self.whitelist),
            "blacklist": list(self.blacklist),
            "default_action": self.default_action.value,
            "global_feature_flags": self.global_feature_flags,
            "plugin_policies": {
                k: v.to_dict() for k, v in self.plugin_policies.items()
            },
            "protected_plugins": list(self.protected_plugins),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceConfig":
        """Create from dictionary."""
        mode = ListMode.DISABLED
        if data.get("mode"):
            try:
                mode = ListMode(data["mode"])
            except ValueError:
                pass
        
        default_action = PolicyAction.BLOCK
        if data.get("default_action"):
            try:
                default_action = PolicyAction(data["default_action"])
            except ValueError:
                pass
        
        plugin_policies = {}
        for k, v in data.get("plugin_policies", {}).items():
            if isinstance(v, dict):
                v["plugin_id"] = k
                plugin_policies[k] = PluginPolicy.from_dict(v)
        
        return cls(
            mode=mode,
            whitelist=set(data.get("whitelist", [])),
            blacklist=set(data.get("blacklist", [])),
            default_action=default_action,
            global_feature_flags=data.get("global_feature_flags", {}),
            plugin_policies=plugin_policies,
            protected_plugins=set(data.get("protected_plugins", [])),
        )


@dataclass
class PolicyCheckResult:
    """Result of a policy check."""
    
    allowed: bool
    action: PolicyAction
    reason: str = ""
    plugin_id: str = ""
    policy_type: str = ""  # "whitelist", "blacklist", "policy", "feature_flag"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "reason": self.reason,
            "plugin_id": self.plugin_id,
            "policy_type": self.policy_type,
        }


# =============================================================================
# GOVERNANCE MANAGER
# =============================================================================

class GovernanceManager:
    """Central manager for plugin governance.
    
    Controls:
    - Whitelist/blacklist for plugin installation
    - Feature flags per plugin
    - Policy enforcement
    """
    
    def __init__(
        self,
        config: Optional[GovernanceConfig] = None,
        config_path: Optional[Path] = None,
    ):
        """Initialize governance manager.
        
        Args:
            config: Configuration options
            config_path: Path to persist configuration
        """
        self._config = config or GovernanceConfig()
        self._config_path = config_path
        self._lock = Lock()
        
        # Callbacks for policy violations
        self._violation_callbacks: List[Callable[[PolicyCheckResult], None]] = []
        
        # Stats
        self._checks_performed: int = 0
        self._violations_blocked: int = 0
        self._violations_warned: int = 0
        
        # Load from file if exists
        if config_path and config_path.exists():
            self._load_config()
    
    @property
    def config(self) -> GovernanceConfig:
        """Get current configuration."""
        return self._config
    
    @property
    def mode(self) -> ListMode:
        """Get current list mode."""
        return self._config.mode
    
    # -------------------------------------------------------------------------
    # LIST MANAGEMENT
    # -------------------------------------------------------------------------
    
    def set_mode(self, mode: ListMode) -> None:
        """Set the list mode.
        
        Args:
            mode: New list mode
        """
        with self._lock:
            self._config.mode = mode
        self._save_config()
        logger.info("Governance mode set to: %s", mode.value)
    
    def add_to_whitelist(self, plugin_id: str) -> bool:
        """Add a plugin to the whitelist.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if added, False if already present
        """
        with self._lock:
            if plugin_id in self._config.whitelist:
                return False
            self._config.whitelist.add(plugin_id)
        self._save_config()
        logger.info("Added to whitelist: %s", plugin_id)
        return True
    
    def remove_from_whitelist(self, plugin_id: str) -> bool:
        """Remove a plugin from the whitelist.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if removed, False if not present
        """
        with self._lock:
            if plugin_id not in self._config.whitelist:
                return False
            self._config.whitelist.remove(plugin_id)
        self._save_config()
        logger.info("Removed from whitelist: %s", plugin_id)
        return True
    
    def add_to_blacklist(self, plugin_id: str, reason: str = "") -> bool:
        """Add a plugin to the blacklist.
        
        Args:
            plugin_id: Plugin identifier
            reason: Reason for blacklisting
            
        Returns:
            True if added, False if already present
        """
        # Check if protected
        if plugin_id in self._config.protected_plugins:
            logger.warning(
                "Cannot blacklist protected plugin: %s", plugin_id
            )
            return False
        
        with self._lock:
            if plugin_id in self._config.blacklist:
                return False
            self._config.blacklist.add(plugin_id)
            # Also update policy
            if plugin_id not in self._config.plugin_policies:
                self._config.plugin_policies[plugin_id] = PluginPolicy(
                    plugin_id=plugin_id
                )
            self._config.plugin_policies[plugin_id].allowed = False
            self._config.plugin_policies[plugin_id].reason = reason
        self._save_config()
        logger.info("Added to blacklist: %s (reason: %s)", plugin_id, reason)
        return True
    
    def remove_from_blacklist(self, plugin_id: str) -> bool:
        """Remove a plugin from the blacklist.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if removed, False if not present
        """
        with self._lock:
            if plugin_id not in self._config.blacklist:
                return False
            self._config.blacklist.remove(plugin_id)
            # Update policy
            if plugin_id in self._config.plugin_policies:
                self._config.plugin_policies[plugin_id].allowed = True
                self._config.plugin_policies[plugin_id].reason = ""
        self._save_config()
        logger.info("Removed from blacklist: %s", plugin_id)
        return True
    
    def get_whitelist(self) -> List[str]:
        """Get the current whitelist."""
        return list(self._config.whitelist)
    
    def get_blacklist(self) -> List[str]:
        """Get the current blacklist."""
        return list(self._config.blacklist)
    
    # -------------------------------------------------------------------------
    # POLICY CHECKS
    # -------------------------------------------------------------------------
    
    def is_plugin_allowed(self, plugin_id: str) -> bool:
        """Check if a plugin is allowed.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if allowed
        """
        result = self.check_plugin_allowed(plugin_id)
        return result.allowed
    
    def check_plugin_allowed(self, plugin_id: str) -> PolicyCheckResult:
        """Check if a plugin is allowed with detailed result.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PolicyCheckResult with details
        """
        self._checks_performed += 1
        
        # Check mode
        if self._config.mode == ListMode.DISABLED:
            return PolicyCheckResult(
                allowed=True,
                action=PolicyAction.ALLOW,
                plugin_id=plugin_id,
                policy_type="disabled",
            )
        
        # Whitelist mode
        if self._config.mode == ListMode.WHITELIST:
            if plugin_id in self._config.whitelist:
                return PolicyCheckResult(
                    allowed=True,
                    action=PolicyAction.ALLOW,
                    plugin_id=plugin_id,
                    policy_type="whitelist",
                )
            else:
                result = PolicyCheckResult(
                    allowed=False,
                    action=self._config.default_action,
                    reason=f"Plugin '{plugin_id}' is not in whitelist",
                    plugin_id=plugin_id,
                    policy_type="whitelist",
                )
                self._handle_violation(result)
                return result
        
        # Blacklist mode
        if self._config.mode == ListMode.BLACKLIST:
            if plugin_id in self._config.blacklist:
                # Get reason from policy if available
                reason = f"Plugin '{plugin_id}' is blacklisted"
                if plugin_id in self._config.plugin_policies:
                    policy_reason = self._config.plugin_policies[plugin_id].reason
                    if policy_reason:
                        reason = policy_reason
                
                result = PolicyCheckResult(
                    allowed=False,
                    action=self._config.default_action,
                    reason=reason,
                    plugin_id=plugin_id,
                    policy_type="blacklist",
                )
                self._handle_violation(result)
                return result
            else:
                return PolicyCheckResult(
                    allowed=True,
                    action=PolicyAction.ALLOW,
                    plugin_id=plugin_id,
                    policy_type="blacklist",
                )
        
        # Default allow
        return PolicyCheckResult(
            allowed=True,
            action=PolicyAction.ALLOW,
            plugin_id=plugin_id,
            policy_type="default",
        )
    
    # -------------------------------------------------------------------------
    # FEATURE FLAGS
    # -------------------------------------------------------------------------
    
    def is_feature_enabled(
        self,
        plugin_id: str,
        feature_name: str,
        dev_mode: bool = False,
    ) -> bool:
        """Check if a feature is enabled for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            feature_name: Feature name
            dev_mode: Whether dev mode is active
            
        Returns:
            True if feature is enabled
        """
        # Check global flag first
        if feature_name in self._config.global_feature_flags:
            if not self._config.global_feature_flags[feature_name]:
                return False
        
        # Check plugin-specific flag
        if plugin_id in self._config.plugin_policies:
            policy = self._config.plugin_policies[plugin_id]
            if feature_name in policy.feature_flags:
                flag = policy.feature_flags[feature_name]
                
                # Check if requires dev mode
                if flag.requires_dev_mode and not dev_mode:
                    return False
                
                return flag.enabled
        
        # Default to enabled
        return True
    
    def set_feature_flag(
        self,
        plugin_id: str,
        feature_name: str,
        enabled: bool,
        description: str = "",
        requires_dev_mode: bool = False,
    ) -> None:
        """Set a feature flag for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            feature_name: Feature name
            enabled: Whether feature is enabled
            description: Description of the feature
            requires_dev_mode: Whether feature requires dev mode
        """
        with self._lock:
            if plugin_id not in self._config.plugin_policies:
                self._config.plugin_policies[plugin_id] = PluginPolicy(
                    plugin_id=plugin_id
                )
            
            self._config.plugin_policies[plugin_id].feature_flags[feature_name] = FeatureFlag(
                name=feature_name,
                enabled=enabled,
                description=description,
                requires_dev_mode=requires_dev_mode,
            )
        
        self._save_config()
        logger.info(
            "Feature flag set: %s.%s = %s",
            plugin_id, feature_name, enabled
        )
    
    def remove_feature_flag(self, plugin_id: str, feature_name: str) -> bool:
        """Remove a feature flag.
        
        Args:
            plugin_id: Plugin identifier
            feature_name: Feature name
            
        Returns:
            True if removed
        """
        with self._lock:
            if plugin_id not in self._config.plugin_policies:
                return False
            
            policy = self._config.plugin_policies[plugin_id]
            if feature_name not in policy.feature_flags:
                return False
            
            del policy.feature_flags[feature_name]
        
        self._save_config()
        logger.info("Feature flag removed: %s.%s", plugin_id, feature_name)
        return True
    
    def get_feature_flags(self, plugin_id: str) -> Dict[str, FeatureFlag]:
        """Get all feature flags for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Dictionary of feature flags
        """
        if plugin_id not in self._config.plugin_policies:
            return {}
        return dict(self._config.plugin_policies[plugin_id].feature_flags)
    
    def set_global_feature_flag(self, feature_name: str, enabled: bool) -> None:
        """Set a global feature flag.
        
        Args:
            feature_name: Feature name
            enabled: Whether feature is enabled
        """
        with self._lock:
            self._config.global_feature_flags[feature_name] = enabled
        self._save_config()
        logger.info("Global feature flag set: %s = %s", feature_name, enabled)
    
    def get_global_feature_flags(self) -> Dict[str, bool]:
        """Get all global feature flags."""
        return dict(self._config.global_feature_flags)
    
    # -------------------------------------------------------------------------
    # PLUGIN POLICIES
    # -------------------------------------------------------------------------
    
    def get_plugin_policy(self, plugin_id: str) -> Optional[PluginPolicy]:
        """Get policy for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            PluginPolicy or None
        """
        return self._config.plugin_policies.get(plugin_id)
    
    def set_plugin_policy(self, policy: PluginPolicy) -> None:
        """Set policy for a plugin.
        
        Args:
            policy: Plugin policy
        """
        with self._lock:
            self._config.plugin_policies[policy.plugin_id] = policy
        self._save_config()
        logger.info("Plugin policy set: %s", policy.plugin_id)
    
    def remove_plugin_policy(self, plugin_id: str) -> bool:
        """Remove policy for a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if removed
        """
        with self._lock:
            if plugin_id not in self._config.plugin_policies:
                return False
            del self._config.plugin_policies[plugin_id]
        self._save_config()
        logger.info("Plugin policy removed: %s", plugin_id)
        return True
    
    def get_all_policies(self) -> Dict[str, PluginPolicy]:
        """Get all plugin policies."""
        return dict(self._config.plugin_policies)
    
    # -------------------------------------------------------------------------
    # PROTECTED PLUGINS
    # -------------------------------------------------------------------------
    
    def add_protected_plugin(self, plugin_id: str) -> bool:
        """Mark a plugin as protected (cannot be disabled/blacklisted).
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if added
        """
        with self._lock:
            if plugin_id in self._config.protected_plugins:
                return False
            self._config.protected_plugins.add(plugin_id)
        self._save_config()
        logger.info("Plugin marked as protected: %s", plugin_id)
        return True
    
    def remove_protected_plugin(self, plugin_id: str) -> bool:
        """Remove protection from a plugin.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if removed
        """
        with self._lock:
            if plugin_id not in self._config.protected_plugins:
                return False
            self._config.protected_plugins.remove(plugin_id)
        self._save_config()
        logger.info("Plugin protection removed: %s", plugin_id)
        return True
    
    def is_protected(self, plugin_id: str) -> bool:
        """Check if a plugin is protected.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            True if protected
        """
        return plugin_id in self._config.protected_plugins
    
    def get_protected_plugins(self) -> List[str]:
        """Get list of protected plugins."""
        return list(self._config.protected_plugins)
    
    # -------------------------------------------------------------------------
    # VIOLATION HANDLING
    # -------------------------------------------------------------------------
    
    def _handle_violation(self, result: PolicyCheckResult) -> None:
        """Handle a policy violation.
        
        Args:
            result: The violation result
        """
        if result.action == PolicyAction.BLOCK:
            self._violations_blocked += 1
            logger.warning(
                "Policy violation BLOCKED: %s - %s",
                result.plugin_id, result.reason
            )
        elif result.action == PolicyAction.WARN:
            self._violations_warned += 1
            logger.warning(
                "Policy violation WARNING: %s - %s",
                result.plugin_id, result.reason
            )
        
        # Notify callbacks
        for callback in self._violation_callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error("Violation callback failed: %s", e)
    
    def add_violation_callback(
        self,
        callback: Callable[[PolicyCheckResult], None],
    ) -> None:
        """Add a callback for policy violations.
        
        Args:
            callback: Function to call on violations
        """
        self._violation_callbacks.append(callback)
    
    def remove_violation_callback(
        self,
        callback: Callable[[PolicyCheckResult], None],
    ) -> bool:
        """Remove a violation callback.
        
        Returns:
            True if removed
        """
        try:
            self._violation_callbacks.remove(callback)
            return True
        except ValueError:
            return False
    
    # -------------------------------------------------------------------------
    # PERSISTENCE
    # -------------------------------------------------------------------------
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self._config_path or not self._config_path.exists():
            return
        
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._config = GovernanceConfig.from_dict(data)
            logger.debug("Loaded governance config from %s", self._config_path)
        except Exception as e:
            logger.error("Failed to load governance config: %s", e)
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        if not self._config_path:
            return
        
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config.to_dict(), f, indent=2)
            logger.debug("Saved governance config to %s", self._config_path)
        except Exception as e:
            logger.error("Failed to save governance config: %s", e)
    
    def reload_config(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    # -------------------------------------------------------------------------
    # STATUS & STATS
    # -------------------------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return {
            "mode": self._config.mode.value,
            "whitelist_count": len(self._config.whitelist),
            "blacklist_count": len(self._config.blacklist),
            "policy_count": len(self._config.plugin_policies),
            "protected_count": len(self._config.protected_plugins),
            "global_flags_count": len(self._config.global_feature_flags),
            "checks_performed": self._checks_performed,
            "violations_blocked": self._violations_blocked,
            "violations_warned": self._violations_warned,
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get governance status."""
        return {
            "mode": self._config.mode.value,
            "default_action": self._config.default_action.value,
            "whitelist": list(self._config.whitelist),
            "blacklist": list(self._config.blacklist),
            "protected_plugins": list(self._config.protected_plugins),
            "global_feature_flags": self._config.global_feature_flags,
            "policy_count": len(self._config.plugin_policies),
        }
    
    def update_config(self, config: GovernanceConfig) -> None:
        """Update the entire configuration.
        
        Args:
            config: New configuration
        """
        with self._lock:
            self._config = config
        self._save_config()
        logger.info("Governance configuration updated")


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_governance: Optional[GovernanceManager] = None
_governance_lock = Lock()


def get_governance() -> GovernanceManager:
    """Get the global governance manager.
    
    Returns:
        The global GovernanceManager instance
    """
    global _governance
    
    with _governance_lock:
        if _governance is None:
            _governance = GovernanceManager()
    
    return _governance


def init_governance(
    config: Optional[GovernanceConfig] = None,
    config_path: Optional[Path] = None,
) -> GovernanceManager:
    """Initialize or reinitialize the global governance manager.
    
    Args:
        config: Configuration options
        config_path: Path to persist configuration
        
    Returns:
        The initialized GovernanceManager
    """
    global _governance
    
    with _governance_lock:
        _governance = GovernanceManager(config=config, config_path=config_path)
    
    logger.info("Global governance manager initialized")
    return _governance


def reset_governance() -> None:
    """Reset the global governance manager."""
    global _governance
    
    with _governance_lock:
        _governance = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_plugin_allowed(plugin_id: str) -> bool:
    """Check if a plugin is allowed.
    
    Args:
        plugin_id: Plugin identifier
        
    Returns:
        True if allowed
    """
    return get_governance().is_plugin_allowed(plugin_id)


def check_plugin_allowed(plugin_id: str) -> PolicyCheckResult:
    """Check if a plugin is allowed with details.
    
    Args:
        plugin_id: Plugin identifier
        
    Returns:
        PolicyCheckResult
    """
    return get_governance().check_plugin_allowed(plugin_id)


def is_feature_enabled(
    plugin_id: str,
    feature_name: str,
    dev_mode: bool = False,
) -> bool:
    """Check if a feature is enabled.
    
    Args:
        plugin_id: Plugin identifier
        feature_name: Feature name
        dev_mode: Whether dev mode is active
        
    Returns:
        True if enabled
    """
    return get_governance().is_feature_enabled(plugin_id, feature_name, dev_mode)


def add_to_whitelist(plugin_id: str) -> bool:
    """Add a plugin to the whitelist.
    
    Args:
        plugin_id: Plugin identifier
        
    Returns:
        True if added
    """
    return get_governance().add_to_whitelist(plugin_id)


def add_to_blacklist(plugin_id: str, reason: str = "") -> bool:
    """Add a plugin to the blacklist.
    
    Args:
        plugin_id: Plugin identifier
        reason: Reason for blacklisting
        
    Returns:
        True if added
    """
    return get_governance().add_to_blacklist(plugin_id, reason)


def set_feature_flag(
    plugin_id: str,
    feature_name: str,
    enabled: bool,
) -> None:
    """Set a feature flag.
    
    Args:
        plugin_id: Plugin identifier
        feature_name: Feature name
        enabled: Whether enabled
    """
    get_governance().set_feature_flag(plugin_id, feature_name, enabled)


def get_governance_status() -> Dict[str, Any]:
    """Get governance status.
    
    Returns:
        Status dictionary
    """
    return get_governance().get_status()
