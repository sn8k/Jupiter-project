# Changelog: jupiter/core/bridge/governance.py

## [0.1.0] - Initial Implementation

### Added
- `ListMode` enum for governance mode (DISABLED, WHITELIST, BLACKLIST)
- `PolicyAction` enum for actions (ALLOW, BLOCK, WARN)
- `FeatureFlag` dataclass for feature flag management:
  - name, enabled, description
  - requires_dev_mode, requires_permissions
  - deprecated, deprecation_message
  - conditions for dynamic evaluation
  - to_dict/from_dict serialization
- `PluginPolicy` dataclass for per-plugin policies:
  - plugin_id, allowed, reason
  - feature_flags, allowed_operations, denied_operations
  - max_jobs, priority, custom_data
  - to_dict/from_dict serialization
- `GovernanceConfig` dataclass for global configuration:
  - mode, whitelist, blacklist
  - global_feature_flags, plugin_policies
  - default_action, protected_plugins
  - to_dict/from_dict serialization
- `PolicyCheckResult` dataclass for check results:
  - allowed, action, reason, plugin_id, policy_type
  - timestamp, metadata
  - to_dict serialization
- `GovernanceManager` class - main governance controller:
  - Configuration management with JSON persistence
  - Whitelist/blacklist methods: add_to_*, remove_from_*, get_*
  - Policy checks: is_plugin_allowed(), check_plugin_allowed()
  - Feature flags: is_feature_enabled(), set_feature_flag(), set_global_feature_flag()
  - Plugin policies: get_plugin_policy(), set_plugin_policy(), remove_plugin_policy()
  - Protected plugins: add_protected_plugin(), remove_protected_plugin(), is_protected()
  - Violation callbacks for audit integration
  - Statistics tracking: get_stats(), get_status()
  - Configuration reload and update methods
- Global singleton pattern:
  - get_governance(), init_governance(), reset_governance()
- Convenience functions:
  - is_plugin_allowed(), check_plugin_allowed()
  - is_feature_enabled(), set_feature_flag()
  - add_to_whitelist(), add_to_blacklist()
  - get_governance_status()
- Thread-safe implementation with Lock
- Full JSON persistence support
- Integration ready with bridge bootstrap

### Features
- Three governance modes: Disabled (allow all), Whitelist (deny by default), Blacklist (allow by default)
- Per-plugin feature flags with dev mode requirements
- Global feature flags that override plugin-level flags
- Protected plugins that cannot be blacklisted
- Violation callback system for audit logging
- Custom blacklist reasons for documentation
- Full serialization for config persistence

### Tests
- 75 tests in test_bridge_governance.py covering:
  - All enums and dataclasses
  - Whitelist/blacklist operations
  - Feature flag management
  - Protected plugins
  - Violation callbacks
  - Persistence (save/load/reload)
  - Integration scenarios
  - Global convenience functions
