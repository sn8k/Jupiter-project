# Changelog – jupiter/web (Files View)

## [2025-01-XX] – Major UI Refactoring

### Changed
- **Files view layout**: Refactored from simple table to a two-column layout with:
  - **Left help panel**: Sticky sidebar with documentation about columns, actions, simulator, and tips
  - **Main content area**: Enhanced table with toolbar (search, filter, stats)

### Added
- **Search functionality**: Real-time filtering by file path (`files-search` input)
- **Type filter**: Dropdown to filter by file extension (`.py`, `.js`, `.ts`, `.html`, `.css`, `.json`, `.md`)
- **Stats badges**: Live count of files and total size displayed in toolbar
- **File icons**: Visual icons based on file extension (📄, 🐍, ⚡, 🔷, 🌐, 🎨, 📋, 📝)
- **Type column**: Displays file extension with styled badge
- **Simulator button**: Changed from 🗑️ (trash) to 🔬 (microscope) for clearer intent
- **Help panel sections**:
  - Table columns explanation
  - Available actions guide
  - Simulator description
  - Usage tips

### i18n
- Added 21 new translation keys for Files view:
  - `files_type`, `files_actions`
  - `files_search_placeholder`, `files_filter_all`, `files_count`
  - `files_help_title`, `files_help_intro`
  - `files_help_columns_title`, `files_help_columns_path`, `files_help_columns_type`, `files_help_columns_size`, `files_help_columns_modified`, `files_help_columns_funcs`
  - `files_help_actions_title`, `files_help_actions_simulate`
  - `files_help_simulator_title`, `files_help_simulator_desc`
  - `files_help_tips_title`, `files_help_tips_search`, `files_help_tips_filter`, `files_help_tips_sort`
  - `files_simulate_tooltip`

### CSS
- Added `.files-layout` grid (280px sidebar + 1fr main)
- Added `.files-help-panel` with sticky positioning
- Added `.files-toolbar` flex layout
- Added `.files-stats` badges styling
- Added `.files-table` enhancements:
  - `.file-path`, `.file-icon`, `.file-name`
  - `.type-badge` monospace styling
  - `.func-count` green badge
  - `.simulate-btn` accent-colored button

### JavaScript
- Enhanced `renderFiles()` function with:
  - `getFileExtension()` helper
  - `getFileIcon()` helper (extension-based icons)
  - Search filter event listener
  - Type filter event listener
  - Stats badge updates

### UX Improvements
- Simulator action icon changed from trash (🗑️) to microscope (🔬) to better represent "impact analysis" intent
- Added responsive design (help panel hidden on mobile)
- Improved visual hierarchy with icons and badges
