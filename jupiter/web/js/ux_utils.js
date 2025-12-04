/**
 * UX Utilities - Jupiter Bridge Frontend
 * 
 * Provides task-oriented UI controls, progress indicators, and ergonomic improvements.
 * 
 * Features:
 * - Progress indicators (ring, bar, steps)
 * - Task status badges
 * - Skeleton loaders
 * - Debounce/throttle utilities
 * - Focus management
 * - Keyboard navigation helpers
 * - Responsive breakpoint utilities
 * 
 * @version 0.1.0
 * @module jupiter/web/js/ux_utils
 */

(function(window) {
    'use strict';

    const VERSION = '0.1.0';

    // =============================================================================
    // PROGRESS INDICATORS
    // =============================================================================

    /**
     * Create a circular progress ring
     * @param {Object} options
     * @param {number} [options.size=40] - SVG size in pixels
     * @param {number} [options.strokeWidth=4] - Stroke width
     * @param {string} [options.color] - Stroke color (CSS var or hex)
     * @param {number} [options.value=0] - Progress value 0-100
     * @param {boolean} [options.showLabel=true] - Show percentage label
     * @returns {HTMLElement}
     */
    function createProgressRing(options = {}) {
        const {
            size = 40,
            strokeWidth = 4,
            color = 'var(--accent)',
            value = 0,
            showLabel = true
        } = options;

        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (value / 100) * circumference;

        const container = document.createElement('div');
        container.className = 'progress-ring';
        container.style.width = `${size}px`;
        container.style.height = `${size}px`;
        container.style.position = 'relative';

        container.innerHTML = `
            <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
                <circle
                    class="progress-ring-bg"
                    stroke="var(--border)"
                    stroke-width="${strokeWidth}"
                    fill="none"
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                />
                <circle
                    class="progress-ring-progress"
                    stroke="${color}"
                    stroke-width="${strokeWidth}"
                    stroke-linecap="round"
                    fill="none"
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                    style="
                        stroke-dasharray: ${circumference};
                        stroke-dashoffset: ${offset};
                        transform: rotate(-90deg);
                        transform-origin: center;
                    "
                />
            </svg>
            ${showLabel ? `<span class="progress-ring-label" style="
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: ${size / 4}px;
                font-weight: 600;
            ">${Math.round(value)}%</span>` : ''}
        `;

        // Add update method
        container.setProgress = (newValue) => {
            const progress = container.querySelector('.progress-ring-progress');
            const label = container.querySelector('.progress-ring-label');
            const newOffset = circumference - (newValue / 100) * circumference;
            progress.style.strokeDashoffset = newOffset;
            if (label) {
                label.textContent = `${Math.round(newValue)}%`;
            }
        };

        return container;
    }

    /**
     * Create a linear progress bar
     * @param {Object} options
     * @param {number} [options.value=0] - Progress value 0-100
     * @param {string} [options.color] - Bar color
     * @param {boolean} [options.showLabel=false] - Show percentage
     * @param {boolean} [options.striped=false] - Striped animation
     * @param {boolean} [options.indeterminate=false] - Indeterminate animation
     * @returns {HTMLElement}
     */
    function createProgressBar(options = {}) {
        const {
            value = 0,
            color = 'var(--accent)',
            showLabel = false,
            striped = false,
            indeterminate = false
        } = options;

        const container = document.createElement('div');
        container.className = 'progress-bar-container';
        container.style.cssText = `
            position: relative;
            height: 8px;
            background: var(--border);
            border-radius: 4px;
            overflow: hidden;
        `;

        const bar = document.createElement('div');
        bar.className = `progress-bar-fill ${striped ? 'striped' : ''} ${indeterminate ? 'indeterminate' : ''}`;
        bar.style.cssText = `
            height: 100%;
            width: ${indeterminate ? '30%' : value + '%'};
            background: ${color};
            border-radius: 4px;
            transition: width 0.3s ease;
            ${indeterminate ? 'animation: progress-indeterminate 1.5s infinite ease-in-out;' : ''}
            ${striped ? `
                background-image: linear-gradient(
                    45deg,
                    rgba(255,255,255,0.15) 25%,
                    transparent 25%,
                    transparent 50%,
                    rgba(255,255,255,0.15) 50%,
                    rgba(255,255,255,0.15) 75%,
                    transparent 75%
                );
                background-size: 1rem 1rem;
                animation: progress-stripes 1s linear infinite;
            ` : ''}
        `;

        container.appendChild(bar);

        if (showLabel && !indeterminate) {
            const label = document.createElement('span');
            label.className = 'progress-bar-label';
            label.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 10px;
                font-weight: 600;
                color: var(--text-main);
            `;
            label.textContent = `${Math.round(value)}%`;
            container.appendChild(label);
        }

        // Add update method
        container.setProgress = (newValue) => {
            bar.style.width = `${newValue}%`;
            const label = container.querySelector('.progress-bar-label');
            if (label) {
                label.textContent = `${Math.round(newValue)}%`;
            }
        };

        return container;
    }

    /**
     * Create step progress indicator
     * @param {Object} options
     * @param {Array<string>} options.steps - Step labels
     * @param {number} [options.current=0] - Current step index
     * @returns {HTMLElement}
     */
    function createStepProgress(options = {}) {
        const { steps = [], current = 0 } = options;

        const container = document.createElement('div');
        container.className = 'step-progress';
        container.style.cssText = `
            display: flex;
            align-items: center;
            gap: 0;
        `;

        steps.forEach((step, index) => {
            const stepEl = document.createElement('div');
            stepEl.className = `step-item ${index < current ? 'completed' : ''} ${index === current ? 'active' : ''}`;
            stepEl.style.cssText = `
                display: flex;
                flex-direction: column;
                align-items: center;
                flex: 1;
                position: relative;
            `;

            const circle = document.createElement('div');
            circle.className = 'step-circle';
            circle.style.cssText = `
                width: 32px;
                height: 32px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                font-size: 14px;
                background: ${index < current ? 'var(--success)' : index === current ? 'var(--accent)' : 'var(--border)'};
                color: ${index <= current ? 'white' : 'var(--text-muted)'};
                transition: all 0.3s;
            `;
            circle.textContent = index < current ? '✓' : index + 1;

            const label = document.createElement('span');
            label.className = 'step-label';
            label.style.cssText = `
                margin-top: 8px;
                font-size: 12px;
                color: ${index <= current ? 'var(--text-main)' : 'var(--text-muted)'};
                text-align: center;
            `;
            label.textContent = step;

            stepEl.appendChild(circle);
            stepEl.appendChild(label);
            container.appendChild(stepEl);

            // Add connector line
            if (index < steps.length - 1) {
                const connector = document.createElement('div');
                connector.className = 'step-connector';
                connector.style.cssText = `
                    flex: 1;
                    height: 2px;
                    background: ${index < current ? 'var(--success)' : 'var(--border)'};
                    margin: 0 -12px;
                    margin-top: -20px;
                    transition: background 0.3s;
                `;
                container.appendChild(connector);
            }
        });

        // Add setStep method
        container.setStep = (stepIndex) => {
            const items = container.querySelectorAll('.step-item');
            const connectors = container.querySelectorAll('.step-connector');

            items.forEach((item, i) => {
                item.classList.toggle('completed', i < stepIndex);
                item.classList.toggle('active', i === stepIndex);

                const circle = item.querySelector('.step-circle');
                circle.style.background = i < stepIndex ? 'var(--success)' : i === stepIndex ? 'var(--accent)' : 'var(--border)';
                circle.style.color = i <= stepIndex ? 'white' : 'var(--text-muted)';
                circle.textContent = i < stepIndex ? '✓' : i + 1;

                const label = item.querySelector('.step-label');
                label.style.color = i <= stepIndex ? 'var(--text-main)' : 'var(--text-muted)';
            });

            connectors.forEach((conn, i) => {
                conn.style.background = i < stepIndex ? 'var(--success)' : 'var(--border)';
            });
        };

        return container;
    }

    // =============================================================================
    // TASK STATUS BADGES
    // =============================================================================

    const TASK_STATES = {
        pending: { icon: '⏳', label: 'Pending', color: 'var(--warning)' },
        running: { icon: '⚙️', label: 'Running', color: 'var(--accent)' },
        success: { icon: '✓', label: 'Success', color: 'var(--success)' },
        error: { icon: '✕', label: 'Error', color: 'var(--danger)' },
        cancelled: { icon: '⊘', label: 'Cancelled', color: 'var(--text-muted)' }
    };

    /**
     * Create a task status badge
     * @param {string} status - Task status (pending, running, success, error, cancelled)
     * @param {string} [label] - Custom label override
     * @returns {HTMLElement}
     */
    function createTaskStatus(status, label) {
        const state = TASK_STATES[status] || TASK_STATES.pending;
        
        const badge = document.createElement('span');
        badge.className = `task-status ${status}`;
        badge.innerHTML = `<span class="status-icon">${state.icon}</span> ${label || state.label}`;
        badge.style.cssText = `
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
            background: color-mix(in srgb, ${state.color} 20%, transparent);
            color: ${state.color};
        `;

        badge.setStatus = (newStatus, newLabel) => {
            const newState = TASK_STATES[newStatus] || TASK_STATES.pending;
            badge.className = `task-status ${newStatus}`;
            badge.innerHTML = `<span class="status-icon">${newState.icon}</span> ${newLabel || newState.label}`;
            badge.style.background = `color-mix(in srgb, ${newState.color} 20%, transparent)`;
            badge.style.color = newState.color;
        };

        return badge;
    }

    // =============================================================================
    // SKELETON LOADERS
    // =============================================================================

    /**
     * Create a skeleton loader
     * @param {Object} options
     * @param {string} [options.type='text'] - Skeleton type (text, circle, rectangle)
     * @param {string|number} [options.width] - Width
     * @param {string|number} [options.height] - Height
     * @param {number} [options.lines=1] - Number of text lines
     * @returns {HTMLElement}
     */
    function createSkeleton(options = {}) {
        const {
            type = 'text',
            width,
            height,
            lines = 1
        } = options;

        const container = document.createElement('div');
        container.className = 'skeleton-container';

        if (type === 'text') {
            for (let i = 0; i < lines; i++) {
                const line = document.createElement('div');
                line.className = 'skeleton';
                line.style.cssText = `
                    height: ${height || '1em'};
                    width: ${i === lines - 1 && lines > 1 ? '60%' : (width || '100%')};
                    margin-bottom: ${i < lines - 1 ? '8px' : '0'};
                `;
                container.appendChild(line);
            }
        } else if (type === 'circle') {
            const circle = document.createElement('div');
            circle.className = 'skeleton';
            const size = width || height || '40px';
            circle.style.cssText = `
                width: ${size};
                height: ${size};
                border-radius: 50%;
            `;
            container.appendChild(circle);
        } else {
            const rect = document.createElement('div');
            rect.className = 'skeleton';
            rect.style.cssText = `
                width: ${width || '100%'};
                height: ${height || '100px'};
                border-radius: 8px;
            `;
            container.appendChild(rect);
        }

        return container;
    }

    // =============================================================================
    // TIMING UTILITIES
    // =============================================================================

    /**
     * Debounce function execution
     * @param {Function} fn - Function to debounce
     * @param {number} delay - Delay in ms
     * @returns {Function}
     */
    function debounce(fn, delay = 300) {
        let timeoutId;
        
        const debounced = function(...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };

        debounced.cancel = () => clearTimeout(timeoutId);
        return debounced;
    }

    /**
     * Throttle function execution
     * @param {Function} fn - Function to throttle
     * @param {number} limit - Minimum ms between calls
     * @returns {Function}
     */
    function throttle(fn, limit = 100) {
        let inThrottle = false;
        let lastArgs = null;

        return function(...args) {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => {
                    inThrottle = false;
                    if (lastArgs) {
                        fn.apply(this, lastArgs);
                        lastArgs = null;
                    }
                }, limit);
            } else {
                lastArgs = args;
            }
        };
    }

    // =============================================================================
    // FOCUS MANAGEMENT
    // =============================================================================

    /**
     * Trap focus within an element (for modals)
     * @param {HTMLElement} container - Container element
     * @returns {Function} - Cleanup function
     */
    function trapFocus(container) {
        const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
        const focusableElements = container.querySelectorAll(focusableSelector);
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        const handleKeydown = (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstFocusable) {
                    lastFocusable?.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastFocusable) {
                    firstFocusable?.focus();
                    e.preventDefault();
                }
            }
        };

        container.addEventListener('keydown', handleKeydown);
        firstFocusable?.focus();

        return () => container.removeEventListener('keydown', handleKeydown);
    }

    /**
     * Restore focus to previous element after closing modal
     * @returns {Function} - Function to restore focus
     */
    function saveFocus() {
        const previouslyFocused = document.activeElement;
        return () => previouslyFocused?.focus?.();
    }

    // =============================================================================
    // KEYBOARD NAVIGATION
    // =============================================================================

    /**
     * Add keyboard navigation to a list
     * @param {HTMLElement} container - List container
     * @param {Object} options
     * @param {string} [options.itemSelector] - Selector for items
     * @param {Function} [options.onSelect] - Callback when item selected
     * @param {boolean} [options.wrap=true] - Wrap at ends
     * @returns {Function} - Cleanup function
     */
    function addListNavigation(container, options = {}) {
        const {
            itemSelector = '[role="option"], li, .list-item',
            onSelect,
            wrap = true
        } = options;

        let currentIndex = -1;

        const getItems = () => Array.from(container.querySelectorAll(itemSelector));

        const setActive = (index) => {
            const items = getItems();
            if (items.length === 0) return;

            items.forEach((item, i) => {
                item.classList.toggle('keyboard-active', i === index);
                item.setAttribute('aria-selected', i === index ? 'true' : 'false');
            });

            currentIndex = index;
            items[index]?.scrollIntoView({ block: 'nearest' });
        };

        const handleKeydown = (e) => {
            const items = getItems();
            if (items.length === 0) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    if (currentIndex < items.length - 1) {
                        setActive(currentIndex + 1);
                    } else if (wrap) {
                        setActive(0);
                    }
                    break;

                case 'ArrowUp':
                    e.preventDefault();
                    if (currentIndex > 0) {
                        setActive(currentIndex - 1);
                    } else if (wrap) {
                        setActive(items.length - 1);
                    }
                    break;

                case 'Enter':
                case ' ':
                    e.preventDefault();
                    if (currentIndex >= 0 && onSelect) {
                        onSelect(items[currentIndex], currentIndex);
                    }
                    break;

                case 'Home':
                    e.preventDefault();
                    setActive(0);
                    break;

                case 'End':
                    e.preventDefault();
                    setActive(items.length - 1);
                    break;
            }
        };

        container.addEventListener('keydown', handleKeydown);
        container.setAttribute('tabindex', '0');

        return () => container.removeEventListener('keydown', handleKeydown);
    }

    // =============================================================================
    // RESPONSIVE UTILITIES
    // =============================================================================

    const BREAKPOINTS = {
        sm: 640,
        md: 768,
        lg: 1024,
        xl: 1280,
        '2xl': 1536
    };

    /**
     * Check if current viewport matches breakpoint
     * @param {string} breakpoint - Breakpoint name
     * @param {string} [direction='up'] - 'up' for min-width, 'down' for max-width
     * @returns {boolean}
     */
    function matchesBreakpoint(breakpoint, direction = 'up') {
        const width = BREAKPOINTS[breakpoint];
        if (!width) return false;

        if (direction === 'up') {
            return window.innerWidth >= width;
        } else {
            return window.innerWidth < width;
        }
    }

    /**
     * Watch for breakpoint changes
     * @param {string} breakpoint - Breakpoint name
     * @param {Function} callback - Called with (matches: boolean)
     * @returns {Function} - Cleanup function
     */
    function watchBreakpoint(breakpoint, callback) {
        const width = BREAKPOINTS[breakpoint];
        if (!width) return () => {};

        const mediaQuery = window.matchMedia(`(min-width: ${width}px)`);
        
        const handler = (e) => callback(e.matches);
        mediaQuery.addEventListener('change', handler);
        
        // Initial call
        callback(mediaQuery.matches);

        return () => mediaQuery.removeEventListener('change', handler);
    }

    // =============================================================================
    // ANIMATION UTILITIES
    // =============================================================================

    /**
     * Animate element with Web Animations API
     * @param {HTMLElement} element
     * @param {Array} keyframes
     * @param {Object} options
     * @returns {Animation}
     */
    function animate(element, keyframes, options = {}) {
        return element.animate(keyframes, {
            duration: 300,
            easing: 'ease-out',
            fill: 'forwards',
            ...options
        });
    }

    /**
     * Fade in element
     * @param {HTMLElement} element
     * @param {number} [duration=300]
     * @returns {Animation}
     */
    function fadeIn(element, duration = 300) {
        return animate(element, [
            { opacity: 0 },
            { opacity: 1 }
        ], { duration });
    }

    /**
     * Fade out element
     * @param {HTMLElement} element
     * @param {number} [duration=300]
     * @returns {Animation}
     */
    function fadeOut(element, duration = 300) {
        return animate(element, [
            { opacity: 1 },
            { opacity: 0 }
        ], { duration });
    }

    /**
     * Slide down element
     * @param {HTMLElement} element
     * @param {number} [duration=300]
     * @returns {Animation}
     */
    function slideDown(element, duration = 300) {
        element.style.overflow = 'hidden';
        element.style.height = 'auto';
        const height = element.offsetHeight;
        element.style.height = '0';

        return animate(element, [
            { height: '0px', opacity: 0 },
            { height: `${height}px`, opacity: 1 }
        ], { duration }).finished.then(() => {
            element.style.height = '';
            element.style.overflow = '';
        });
    }

    /**
     * Slide up element
     * @param {HTMLElement} element
     * @param {number} [duration=300]
     * @returns {Animation}
     */
    function slideUp(element, duration = 300) {
        element.style.overflow = 'hidden';
        const height = element.offsetHeight;

        return animate(element, [
            { height: `${height}px`, opacity: 1 },
            { height: '0px', opacity: 0 }
        ], { duration }).finished.then(() => {
            element.style.height = '0';
        });
    }

    // =============================================================================
    // COPY TO CLIPBOARD
    // =============================================================================

    /**
     * Copy text to clipboard with fallback
     * @param {string} text
     * @returns {Promise<boolean>}
     */
    async function copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                return true;
            } catch (e) {
                return false;
            } finally {
                document.body.removeChild(textarea);
            }
        }
    }

    // =============================================================================
    // VERSION & PUBLIC API
    // =============================================================================

    function getVersion() {
        return VERSION;
    }

    const uxUtils = {
        // Progress
        createProgressRing,
        createProgressBar,
        createStepProgress,

        // Task status
        createTaskStatus,
        TASK_STATES,

        // Skeletons
        createSkeleton,

        // Timing
        debounce,
        throttle,

        // Focus
        trapFocus,
        saveFocus,

        // Keyboard
        addListNavigation,

        // Responsive
        matchesBreakpoint,
        watchBreakpoint,
        BREAKPOINTS,

        // Animation
        animate,
        fadeIn,
        fadeOut,
        slideDown,
        slideUp,

        // Clipboard
        copyToClipboard,

        // Version
        getVersion
    };

    // Export globally
    window.jupiterUxUtils = uxUtils;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = uxUtils;
    }

})(typeof window !== 'undefined' ? window : this);
