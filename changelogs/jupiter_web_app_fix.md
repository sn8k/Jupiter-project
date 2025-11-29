# Changelog - Web Interface Fixes

## Fixed
- Fixed "frozen" UI issue caused by ES Module scope isolation.
- Removed inline `onclick` handlers in `app.js` and `index.html`.
- Refactored `showOnboarding` and `renderPluginList` to use `data-action` attributes.
- Updated `handleAction` to support `create-config`, `close-onboarding`, and `toggle-plugin`.
- Improved event delegation in `bindActions`.
