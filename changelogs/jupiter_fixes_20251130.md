# Fixes: Version, Plugins, Config, Map

## Changes

- **Frontend**: Corrected displayed version from `v0.1.4` to `v0.1.0` in `app.js` and `index.html`.
- **Server**: Updated API version to `0.1.0` in `api.py`.
- **Build**: Updated `jupiter.spec` to correctly collect `jupiter.plugins` submodules using `collect_submodules`.
- **Config**: Updated `jupiter/config/config.py` to check `%LOCALAPPDATA%/Jupiter/jupiter.yaml` for global configuration.
- **UI**: Improved Live Map visualization in `app.js` by adjusting force simulation parameters (reduced repulsion, added collision, shorter links).

## Impact

- **Version**: Consistent version display across UI and API.
- **Plugins**: Plugins should now be available in the frozen executable.
- **Config**: Users can now store sensitive config in their local app data folder.
- **Map**: The live map should look more structured and less scattered.
