# Changelog – tests/test_cli_plugin_commands.py

## v0.4.0
- Added comprehensive Phase 9 tests (58 tests total, all passing)
- TestInstallComprehensive: 5 tests for install command
  - test_install_with_source_option
  - test_install_with_dry_run
  - test_install_with_dependencies
  - test_install_with_force_option
  - test_install_all_options_combined
- TestUninstallComprehensive: 3 tests for uninstall command
  - test_uninstall_plugin_not_found
  - test_uninstall_plugin_success
  - test_uninstall_with_force
- TestUpdateComprehensive: 7 tests for update command
  - test_update_plugin_not_found
  - test_update_plugin_not_installed
  - test_update_creates_backup
  - test_update_no_backup_option
  - test_update_with_source
  - test_update_with_install_deps
  - test_update_rollback_on_failure
- TestCheckUpdates: 3 tests for check-updates command
  - test_check_updates_no_plugins
  - test_check_updates_with_plugins
  - test_check_updates_json_output
- TestValidateManifest: 4 tests for manifest validation
  - test_validate_valid_manifest
  - test_validate_missing_required_fields
  - test_validate_invalid_version_format
  - test_validate_invalid_plugin_type
- TestInstallDependencies: 3 tests for dependency installation
  - test_install_deps_no_requirements_file
  - test_install_deps_with_requirements_file
  - test_install_deps_pip_failure

## v0.3.0
- Tests for Phase 7.2 signing and verification commands
- TestPluginsSign: 6 tests
- TestPluginsVerify: 3 tests
- TestSignAndVerifyIntegration: 1 test
- TestVerifyPluginSignatureHelper: 4 tests

## v0.2.0
- Tests for basic plugin commands
- TestPluginsList: 3 tests
- TestPluginsInfo: 2 tests
- TestPluginsEnableDisable: 3 tests
- TestPluginsStatus: 2 tests
- TestPluginsScaffold: 2 tests
- TestPluginsInstall: 2 tests
- TestPluginsUninstall: 2 tests
- TestPluginsReload: 2 tests

## v0.1.0
- Initial test file for CLI plugin commands
