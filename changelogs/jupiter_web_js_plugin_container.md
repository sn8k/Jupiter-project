# Changelog - jupiter/web/js/plugin_container.js

## v0.1.0
- Initial creation of PluginContainer module
- Dynamic plugin panel mounting with sandboxed iframe support
- Lazy loading of plugin views from `/api/v1/plugins/{id}/view`
- Event-based communication between host and plugins
- Panel lifecycle management (create, show, hide, destroy)
- Visibility tracking and memory optimization
- Support for message passing via `postMessage`
- Routing integration with plugin navigation
- CSS styling for plugin containers with loading states
- Error handling for plugin load failures
