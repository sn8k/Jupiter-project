# Changelog - WebUI Parity & Enhancements

## Added
- **WebUI Features**:
    - **Scan Options**: Modal to configure `show_hidden`, `incremental`, and `ignore` patterns before scanning.
    - **Run Command**: Modal to execute shell commands with optional dynamic analysis.
    - **Settings Editor**: Full form to edit `jupiter.yaml` (Server, GUI, Meeting, Theme, Language).
    - **Update Interface**: UI to trigger self-update from ZIP or Git.
    - **Live Watch Panel**: Dedicated panel in Dashboard to show real-time file events.
- **API Endpoints**:
    - `GET /config`: Retrieve current configuration.
    - `POST /config`: Update configuration.
    - `POST /update`: Trigger self-update.
- **Core**:
    - `jupiter.core.updater`: Shared logic for self-updates.
    - `jupiter.config.save_config`: Ability to write config back to YAML.

## Changed
- **WebUI**:
    - Replaced placeholder Settings view with functional editor.
    - Updated Dashboard to include Watch panel.
    - Improved `app.js` to handle new modals and actions.
- **Documentation**:
    - Updated `Manual.md`, `docs/user_guide.md`, and `docs/dev_guide.md` to reflect new UI capabilities.
