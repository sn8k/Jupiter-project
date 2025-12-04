# Changelog - jupiter/web/js/ux_utils.js

## [0.1.0] - Initial Release

### Added
- **Progress Indicators**:
  - `createProgressRing()`: Circular SVG progress indicator with percentage label
  - `createProgressBar()`: Linear progress bar with striped/indeterminate modes
  - `createStepProgress()`: Multi-step wizard progress indicator
  
- **Task Status Badges**:
  - `createTaskStatus()`: Status badges for task states
  - States: pending, running, success, error, cancelled
  - Dynamic status updates via `setStatus()` method

- **Skeleton Loaders**:
  - `createSkeleton()`: Loading placeholder components
  - Types: text (multi-line), circle, rectangle
  - Animated shimmer effect

- **Timing Utilities**:
  - `debounce()`: Delay function execution until pause in calls
  - `throttle()`: Limit function execution frequency

- **Focus Management**:
  - `trapFocus()`: Keep keyboard focus within modal/dialog
  - `saveFocus()`: Save and restore focus for modal open/close

- **Keyboard Navigation**:
  - `addListNavigation()`: Arrow key navigation for lists
  - Supports: Up/Down arrows, Home/End, Enter/Space selection
  - Configurable wrap behavior

- **Responsive Utilities**:
  - `matchesBreakpoint()`: Check current viewport against breakpoint
  - `watchBreakpoint()`: React to viewport size changes
  - Breakpoints: sm (640), md (768), lg (1024), xl (1280), 2xl (1536)

- **Animation Utilities**:
  - `animate()`: Web Animations API wrapper
  - `fadeIn()` / `fadeOut()`: Opacity animations
  - `slideDown()` / `slideUp()`: Height animations

- **Clipboard**:
  - `copyToClipboard()`: Copy text with fallback for older browsers

### Features
- Pure vanilla JavaScript, no dependencies
- Consistent with Jupiter design system (CSS variables)
- All components return update methods for dynamic changes
- Cleanup functions for proper memory management
- Accessible ARIA attributes where applicable

### API
All functions exported via `window.jupiterUxUtils`:
- Progress: `createProgressRing`, `createProgressBar`, `createStepProgress`
- Status: `createTaskStatus`, `TASK_STATES`
- Skeletons: `createSkeleton`
- Timing: `debounce`, `throttle`
- Focus: `trapFocus`, `saveFocus`
- Keyboard: `addListNavigation`
- Responsive: `matchesBreakpoint`, `watchBreakpoint`, `BREAKPOINTS`
- Animation: `animate`, `fadeIn`, `fadeOut`, `slideDown`, `slideUp`
- Clipboard: `copyToClipboard`
- Version: `getVersion()`
