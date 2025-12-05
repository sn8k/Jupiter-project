# Changelog - jupiter/web/index.html

## Version 1.0.3 - Backend-injected version placeholders
- Replaced hardcoded `app.js?v=...` and footer badge with `{{JUPITER_VERSION}}` placeholders injected at serve time so the UI shows the running build version.

## 2025-12-03 - Cache-control hardening
- Added no-store/no-cache meta tags and a version comment to prevent browsers from caching the HTML shell.
- Kept the HTML shell authoritative so `styles.css` and `app.js` are always reloaded fresh.

## 2024-12-01
- Split "Interface & Meeting" section into separate "Interface" and "Meeting License" sections.
- New Meeting License panel with status indicator, device key input, auth token input.
- Meeting actions buttons for license verification.
- Last response display area showing raw API response data.

# Changelog - jupiter/web/styles.css (2024-12-01)
- Added `.meeting-section` styles for full-width Meeting panel.
- Added `.meeting-status-box` with colored state variants (status-valid, status-invalid, etc.).
- Added `.meeting-status-indicator` for icon + text status display.
- Added `.meeting-actions` button group styles.
- Added `.meeting-last-response` panel for API response display.
