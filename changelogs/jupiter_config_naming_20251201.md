# Config Naming Update – 2025-12-01

## Changes

- **Global Config**: The install-wide configuration file is now `global_config.yaml`, with automatic fallback to legacy `jupiter.yaml` locations (including `%LOCALAPPDATA%/Jupiter`).
- **Project Configs**: Projects default to `<project>.jupiter.yaml` (derived from the project name/root). Legacy `jupiter.yaml` files are still loaded, but new saves and the raw editor target the new pattern.
- **UI & Docs**: Web UI labels, translations, README, Manual, and guides now describe the new naming scheme and the registry path `~/.jupiter/global_config.yaml`.

## Impact

- Existing projects keep working without renaming, and new projects will be created with the clearer filename convention.
- Administrators can easily distinguish global vs. per-project settings and share configs without collisions.
