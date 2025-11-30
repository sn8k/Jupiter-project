# Changelog - Configuration Split Fix

## Fixed
- **Configuration Persistence**: Fixed an issue where global settings (like Meeting Device Key) were lost when switching projects or scanning different directories.
- **Config Architecture**: Refactored configuration loading and saving to support a split model:
    - **Global Settings** (Server, GUI, Meeting, UI, Plugins) are now saved to `jupiter.yaml` in the installation directory.
    - **Project Settings** (Performance, CI, Backends, API, Security) are saved to `jupiter.yaml` in the project directory.
- **Launch Context**: Updated `JupiterAPIServer` to be aware of the installation path separate from the project root.

## Changed
- `jupiter/config/config.py`: Added `load_merged_config`, `save_global_settings`, `save_project_settings`.
- `jupiter/server/api.py`: Updated `get_config` and `update_config` to use the new split configuration logic.
- `jupiter/cli/main.py`: Updated to pass `install_path` to the server instance.
