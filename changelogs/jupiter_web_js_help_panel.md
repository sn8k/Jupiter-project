# Changelog - jupiter/web/js/help_panel.js

## [0.1.0] - Initial Release

### Added
- **HelpPanel class**: Contextual help panel component for plugin UI
- **Collapsible sections**: Expandable/collapsible help content sections
- **Search functionality**: Filter help content by search term
- **i18n integration**: Support for internationalized help content via i18n_loader
- **Markdown-like formatting**: Simple text formatting for help content
  - Bold text with `**text**`
  - Inline code with backticks
  - Code blocks
  - Lists
- **Keyboard shortcuts**:
  - `F1` to toggle help panel
  - `?` to toggle help panel
  - `Escape` to close
- **Feedback dialog**: Built-in feedback form for user feedback
- **Documentation links**: Support for linking to external documentation
- **Factory function**: `createHelpPanel()` for easy instantiation
- **Context-aware content**: Different help content based on current context

### Features
- Slide-in panel from right side
- Smooth animations and transitions
- Dark/light theme support
- Focus trap when panel is open
- Accessible ARIA attributes
- Event callbacks (onOpen, onClose, onFeedback)

### API
- `show(contextId)`: Show panel with optional context
- `hide()`: Hide panel
- `toggle()`: Toggle visibility
- `setContent(sections)`: Set help content dynamically
- `search(term)`: Filter content by search term
- `showFeedbackDialog()`: Open feedback dialog
- `destroy()`: Clean up and remove panel
- `getVersion()`: Return module version
