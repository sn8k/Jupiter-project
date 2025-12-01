# Changelog – jupiter/web/styles.css
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

