# Changelog - Jupiter Config Fixes

## [0.1.8] - 2024-10-27

### Fixed
- **Configuration Loading**: Added robustness to `JupiterConfig.from_dict` to handle `device_key` alias for `deviceKey` in `meeting` section, ensuring compatibility with different YAML styles.
- **Settings UI**: Improved `loadSettings` in `app.js` to explicitly handle boolean conversion for `meeting_enabled` and ensure `deviceKey` is populated correctly.
- **Logging**: Added debug logging in `api.py` to trace configuration loading issues.
