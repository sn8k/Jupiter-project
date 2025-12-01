# Changelog: Jupiter Plugin UI System

## Overview
This changelog tracks the implementation of the extensible plugin UI system that allows plugins to declare and provide their own menu items and views in the Jupiter web interface.

---

## [1.0.0] - 2025-01-13

### Added

#### Plugin Protocol Extensions (`jupiter/plugins/__init__.py`)
- `PluginUIType` enum with values: `NONE`, `SIDEBAR`, `SETTINGS`, `BOTH`
- `PluginUIConfig` dataclass for plugin UI metadata:
  - `ui_type`: Where the plugin appears (sidebar, settings, or both)
  - `menu_icon`: Emoji or icon for the menu item
  - `menu_label_key`: i18n translation key for the menu label
  - `menu_order`: Numeric order for menu placement (lower = earlier)
  - `view_id`: Unique identifier for the view
- `UIPlugin` Protocol defining the interface for plugins with UI:
  - `ui_config`: Class attribute for UI configuration
  - `get_ui_html()`: Returns HTML content for sidebar views
  - `get_ui_js()`: Returns JavaScript for sidebar views
  - `get_settings_html()`: Returns HTML for settings section
  - `get_settings_js()`: Returns JavaScript for settings section

#### Plugin Manager Extensions (`jupiter/core/plugin_manager.py`)
- `get_sidebar_plugins()`: Returns list of plugins with sidebar UI
- `get_settings_plugins()`: Returns list of plugins with settings UI
- `get_plugin_ui_html(name)`: Retrieves HTML content for a plugin's sidebar view
- `get_plugin_ui_js(name)`: Retrieves JavaScript for a plugin's sidebar view
- `get_plugin_settings_html(name)`: Retrieves HTML for plugin settings
- `get_plugin_settings_js(name)`: Retrieves JavaScript for plugin settings

#### API Endpoints (`jupiter/server/routers/system.py`)
- `GET /plugins/sidebar`: Returns list of plugins with sidebar menu items
- `GET /plugins/settings`: Returns list of plugins with settings sections
- `GET /plugins/{name}/ui`: Returns HTML and JS for a plugin's sidebar view
- `GET /plugins/{name}/settings-ui`: Returns HTML and JS for a plugin's settings

#### Pylance Plugin UI (`jupiter/plugins/pylance_analyzer.py`)
- Added `ui_config` with `PluginUIType.SIDEBAR`
- Implemented `get_ui_html()`: Diagnostic view with stats, file list, and details
- Implemented `get_ui_js()`: Interactive JavaScript for filtering and navigation

#### Notifications Plugin UI (`jupiter/plugins/notifications_webhook.py`)
- Added `ui_config` with `PluginUIType.SETTINGS`
- Implemented `get_settings_html()`: Configuration form for webhook URL and events
- Implemented `get_settings_js()`: Settings management with auto-save and test button

#### Web UI Changes (`jupiter/web/`)
- **index.html**:
  - Added `#plugin-menu-marker` for dynamic menu item insertion
  - Added `#plugin-views-container` for dynamic plugin views
  - Added `#plugin-settings-container` in settings view

- **app.js**:
  - Added `pluginUIState` for tracking loaded plugin UIs
  - `loadPluginMenus()`: Fetches and injects plugin menu items
  - `injectPluginMenuItems()`: Creates nav buttons for sidebar plugins
  - `ensurePluginViewContainer()`: Creates view sections dynamically
  - `bindPluginNavigation()`: Handles plugin view navigation
  - `loadPluginViewContent()`: Loads and injects plugin HTML/JS
  - `loadPluginSettings()`: Loads plugin settings into settings page
  - Updated `setView()` to handle plugin views and settings

- **styles.css**:
  - Plugin view loading state styles
  - Plugin settings container styles
  - Setting row and input styles
  - Stats row and stat card styles
  - Filter bar styles
  - Data table styles for plugin data
  - Severity color classes
  - Warning text styles

#### i18n Translations (`jupiter/web/lang/`)
- Added Pylance-related keys (pylance_view, pylance_title, etc.)
- Added Notifications-related keys (notifications_settings, notifications_url_label, etc.)

---

## Architecture

### How Plugins Declare UI

1. Plugin class defines `ui_config` class attribute with a `PluginUIConfig` instance
2. Plugin implements one or more of the UI methods:
   - `get_ui_html()` + `get_ui_js()` for sidebar views
   - `get_settings_html()` + `get_settings_js()` for settings page

### How UI is Loaded

1. On app init, `loadPluginMenus()` fetches `/plugins/sidebar` and `/plugins/settings`
2. For sidebar plugins, `injectPluginMenuItems()` creates nav buttons before `#plugin-menu-marker`
3. When a plugin view is selected, `loadPluginViewContent()` fetches the HTML/JS from the API
4. When settings view is opened, `loadPluginSettings()` loads all settings plugins' UI

### Plugin Types

| Type | Location | Methods Required |
|------|----------|------------------|
| `SIDEBAR` | Navigation sidebar | `get_ui_html()`, `get_ui_js()` |
| `SETTINGS` | Settings page | `get_settings_html()`, `get_settings_js()` |
| `BOTH` | Both locations | All four methods |
| `NONE` | No UI (default) | None |

---

## Example: Creating a Plugin with UI

```python
from jupiter.plugins import PluginUIConfig, PluginUIType

class Plugin:
    name = "my_plugin"
    version = "1.0.0"
    
    ui_config = PluginUIConfig(
        ui_type=PluginUIType.SIDEBAR,
        menu_icon="🔧",
        menu_label_key="my_plugin_view",
        menu_order=80,
        view_id="my-plugin"
    )
    
    def get_ui_html(self) -> str:
        return "<h2>My Plugin View</h2>"
    
    def get_ui_js(self) -> str:
        return "console.log('My plugin loaded');"
```

---

## Notes

- Plugin UIs are loaded lazily (only when the view is first accessed)
- Settings plugins load all at once when the settings page is opened
- JavaScript is injected as `<script>` tags and executed immediately
- i18n keys should be added to all language files for proper localization
