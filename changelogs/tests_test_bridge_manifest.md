# Changelog - tests/test_bridge_manifest.py

## v1.0.1
- Fixed `test_load_from_file` test to match actual `from_yaml()` behavior
- `source_path` is now the plugin directory (parent of yaml file), not the yaml file itself
- Aligns with manifest.py v0.1.2 change

## v1.0.0
- Initial test suite for PluginManifest class
- Tests for `from_dict()`, `from_yaml()`, validation, optional fields
- Fixtures for minimal and full manifest data
