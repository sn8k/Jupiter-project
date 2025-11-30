# Changelog - jupiter/web/app.js

## [0.1.5] - 2025-11-30
- Exposed `handleLogin`, `openLoginModal`, and `triggerSimulation` to the global `window` object.
- Fixed issue where login button and simulation triggers were not working due to `app.js` being a module.
