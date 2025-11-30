# Changelog – jupiter/core/events.py

## Plugin notification event
- Introduced the `PLUGIN_NOTIFICATION` event type so plugins can broadcast structured messages over the WebSocket channel.
- Keeps the existing event catalogue intact while allowing the UI to differentiate between generic server updates and plugin-emitted alerts.
