# Changelog – jupiter/web/styles.css

## v1.3.0 - Central Logs & Permissions UI

### Added
- `.central-logs-panel`: Central logs panel container with dark theme
- `.central-logs-filters`: Filter bar with grid layout (plugin, level, time, search)
- `.central-logs-content`: Scrollable logs area with monospace font
- `.logs-mini-panel`: Compact log panel for injection in plugin pages
- `.permissions-list`: Grid layout for permission items display
- `.permission-item`: Permission card with icon, name, description
- `.permission-sensitive`: Warning styling for sensitive permissions

## Plugin Activity Widget Styles (Phase 4.2.1)

### Added
- `.plugin-activity-widget`: Base container for activity metrics widget
- `.plugin-activity-widget.disabled`: Muted style for disabled plugins
- `.plugin-activity-widget.loading`: Loading state with spinner animation
- `.activity-stats`: Grid layout for 4-column stat display
- `.activity-stat`: Individual stat card with hover effects
- `.activity-stat.has-errors`: Red highlight for plugins with errors
- `.stat-icon`, `.stat-value`, `.stat-label`: Typography for stat components
- `@keyframes spin`: Loading spinner animation
- Responsive grid (2 columns on mobile)

## Trust Badge & Circuit Breaker Styles

### Added
- `.trust-badge`: Base styling for trust level badges (font-size, padding, border-radius)
- Trust level modifiers:
  - `.trust-badge.official`: Gold/amber color for official plugins
  - `.trust-badge.verified`: Green color for verified plugins
  - `.trust-badge.community`: Blue color for community plugins
  - `.trust-badge.unsigned`: Orange/warning color for unsigned plugins
  - `.trust-badge.experimental`: Purple color for experimental plugins
- `.circuit-breaker`: Base styling for circuit breaker badges
- Circuit breaker state modifiers:
  - `.circuit-breaker.closed`: Green color for healthy state
  - `.circuit-breaker.half-open`: Yellow color for recovery state
  - `.circuit-breaker.open`: Red color for degraded state
- Tooltip support with `title` attribute for all badges

---

- Added global `.hidden` helper to control modal visibility reliably across browsers.
- Introduced `.version-pill`, `.update-box`, et `.version-indicator` pour styliser le badge de version global et la carte de mise à jour dans les paramètres.
- Switched to refreshed dark design system with panel/contrast variables, gradients, and shadowed cards.
- Styled navigation sidebar, action tiles, alerts, live cards, plugin/settings grids, and footer log stream.
- Extended responsive rules for nav compaction, action grids, and header alignment on small screens.
- Added project dashboard styles (hero panel, pill badges, card list, quick-actions grid) plus `.mono` helper and compact stats tweaks.
- Added danger button styling, enforced grid layout for project cards, and kept delete actions visually prominent.
- Added exclusion panel styles (`.project-ignore-panel`, `.ignore-entries-grid`, `.ignore-entry`, `.ignore-custom-patterns`) with visual feedback for ignored items (strikethrough, warning tint) and hidden file handling.
- Added projects page section styles for visual separation: `.active-project-section` with accent border and `.projects-list-section` for the list.
- Introduit `.settings-columns`, `.settings-side-column`, `.plugin-settings-card`, `.setting-btn`, `.setting-result` etc. afin de supporter la nouvelle grille deux colonnes, la carte Mise à jour en colonne latérale et les panneaux plugins persistants avec retours d'état.

