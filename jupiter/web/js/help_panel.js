/**
 * Help Panel - Jupiter Bridge Frontend
 * 
 * Provides contextual help for plugin UI panels.
 * Features:
 * - Dynamic help content loading from i18n files
 * - Collapsible sections
 * - Links to documentation
 * - Keyboard shortcuts reference
 * - Accessibility for novices
 * 
 * @version 0.1.0
 * @module jupiter/web/js/help_panel
 */

(function(window) {
    'use strict';

    const VERSION = '0.1.0';

    /**
     * Help Panel Component
     */
    class HelpPanel {
        /**
         * @param {Object} options - Configuration options
         * @param {string} [options.position='right'] - Panel position ('right', 'left', 'bottom')
         * @param {number} [options.width=320] - Panel width in pixels
         * @param {boolean} [options.collapsible=true] - Allow collapsing sections
         * @param {string} [options.docsBaseUrl=''] - Base URL for documentation links
         */
        constructor(options = {}) {
            this.options = {
                position: options.position || 'right',
                width: options.width || 320,
                collapsible: options.collapsible !== false,
                docsBaseUrl: options.docsBaseUrl || '',
                containerClass: options.containerClass || 'help-panel',
                ...options
            };

            this.element = null;
            this.pluginId = null;
            this.helpContent = null;
            this.isExpanded = true;
            this.activeSection = null;
            
            // i18n integration
            this.i18n = options.i18n || window.jupiterBridge?.i18n || null;
        }

        /**
         * Render the help panel
         * @param {string|HTMLElement} container - Container element or selector
         * @returns {HTMLElement} The panel element
         */
        render(container) {
            const panel = document.createElement('aside');
            panel.className = `${this.options.containerClass} ${this.options.position}`;
            panel.setAttribute('role', 'complementary');
            panel.setAttribute('aria-label', this._t('help_panel_label', 'Help'));
            panel.style.width = `${this.options.width}px`;

            panel.innerHTML = `
                <div class="help-panel-header">
                    <h3 class="help-panel-title">
                        <span class="help-icon">❓</span>
                        <span data-i18n="help_title">${this._t('help_title', 'Help')}</span>
                    </h3>
                    <div class="help-panel-actions">
                        <button class="btn btn-sm btn-ghost help-toggle" 
                                title="${this._t('toggle_help', 'Toggle help panel')}"
                                aria-expanded="true">
                            <span class="icon">◀</span>
                        </button>
                    </div>
                </div>
                <div class="help-panel-body">
                    <div class="help-search">
                        <input type="search" 
                               class="help-search-input" 
                               placeholder="${this._t('search_help', 'Search help...')}"
                               aria-label="${this._t('search_help', 'Search help')}">
                    </div>
                    <div class="help-content">
                        <div class="help-loading" style="display: none;">
                            <span class="spinner"></span>
                            <span data-i18n="loading">${this._t('loading', 'Loading...')}</span>
                        </div>
                        <div class="help-sections"></div>
                    </div>
                    <div class="help-footer">
                        <a href="#" class="help-docs-link" target="_blank" rel="noopener">
                            <span class="icon">📖</span>
                            <span data-i18n="full_documentation">${this._t('full_documentation', 'Full Documentation')}</span>
                        </a>
                        <button class="btn btn-sm btn-link help-feedback">
                            <span class="icon">💬</span>
                            <span data-i18n="send_feedback">${this._t('send_feedback', 'Send Feedback')}</span>
                        </button>
                    </div>
                </div>
            `;

            this.element = panel;
            this._cacheElements();
            this._bindEvents();

            // Append to container
            if (container) {
                if (typeof container === 'string') {
                    container = document.querySelector(container);
                }
                if (container) {
                    container.appendChild(panel);
                }
            }

            return panel;
        }

        /**
         * Cache DOM elements
         * @private
         */
        _cacheElements() {
            this.elements = {
                header: this.element.querySelector('.help-panel-header'),
                body: this.element.querySelector('.help-panel-body'),
                toggleBtn: this.element.querySelector('.help-toggle'),
                searchInput: this.element.querySelector('.help-search-input'),
                content: this.element.querySelector('.help-content'),
                sections: this.element.querySelector('.help-sections'),
                loading: this.element.querySelector('.help-loading'),
                docsLink: this.element.querySelector('.help-docs-link'),
                feedbackBtn: this.element.querySelector('.help-feedback')
            };
        }

        /**
         * Bind event handlers
         * @private
         */
        _bindEvents() {
            // Toggle panel
            this.elements.toggleBtn?.addEventListener('click', () => this.toggle());

            // Search
            let searchTimeout;
            this.elements.searchInput?.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this._filterSections(e.target.value);
                }, 200);
            });

            // Feedback button
            this.elements.feedbackBtn?.addEventListener('click', () => this._showFeedbackDialog());

            // Keyboard shortcut (F1 or ?)
            document.addEventListener('keydown', (e) => {
                if (e.key === 'F1' || (e.key === '?' && !this._isInputFocused())) {
                    e.preventDefault();
                    this.toggle();
                }
            });
        }

        /**
         * Load help content for a plugin
         * @param {string} pluginId - Plugin identifier
         * @returns {Promise<void>}
         */
        async loadPluginHelp(pluginId) {
            this.pluginId = pluginId;
            this._showLoading(true);

            try {
                // Try to load from i18n
                const helpContent = await this._fetchHelpContent(pluginId);
                this.helpContent = helpContent;
                this._renderSections(helpContent);

                // Update docs link
                if (this.elements.docsLink && this.options.docsBaseUrl) {
                    this.elements.docsLink.href = `${this.options.docsBaseUrl}/plugins/${pluginId}`;
                }

                console.log(`[HelpPanel] Loaded help for ${pluginId}`);

            } catch (error) {
                console.error(`[HelpPanel] Failed to load help for ${pluginId}:`, error);
                this._renderError(error.message);
            } finally {
                this._showLoading(false);
            }
        }

        /**
         * Fetch help content from API or i18n
         * @private
         */
        async _fetchHelpContent(pluginId) {
            // Try API first
            try {
                const response = await fetch(`/api/v1/plugins/${pluginId}/help`);
                if (response.ok) {
                    return await response.json();
                }
            } catch (e) {
                // API not available, try i18n
            }

            // Build from i18n keys
            return this._buildHelpFromI18n(pluginId);
        }

        /**
         * Build help content from i18n keys
         * @private
         */
        _buildHelpFromI18n(pluginId) {
            const sections = [];

            // Overview section
            const overview = this._t(`plugin.${pluginId}.help_overview`);
            if (overview && overview !== `plugin.${pluginId}.help_overview`) {
                sections.push({
                    id: 'overview',
                    title: this._t('help_overview', 'Overview'),
                    icon: '📋',
                    content: overview
                });
            }

            // Getting started
            const gettingStarted = this._t(`plugin.${pluginId}.help_getting_started`);
            if (gettingStarted && gettingStarted !== `plugin.${pluginId}.help_getting_started`) {
                sections.push({
                    id: 'getting-started',
                    title: this._t('help_getting_started', 'Getting Started'),
                    icon: '🚀',
                    content: gettingStarted
                });
            }

            // Features
            const features = this._t(`plugin.${pluginId}.help_features`);
            if (features && features !== `plugin.${pluginId}.help_features`) {
                sections.push({
                    id: 'features',
                    title: this._t('help_features', 'Features'),
                    icon: '✨',
                    content: features
                });
            }

            // Usage
            const usage = this._t(`plugin.${pluginId}.help_usage`);
            if (usage && usage !== `plugin.${pluginId}.help_usage`) {
                sections.push({
                    id: 'usage',
                    title: this._t('help_usage', 'How to Use'),
                    icon: '📝',
                    content: usage
                });
            }

            // Shortcuts
            const shortcuts = this._t(`plugin.${pluginId}.help_shortcuts`);
            if (shortcuts && shortcuts !== `plugin.${pluginId}.help_shortcuts`) {
                sections.push({
                    id: 'shortcuts',
                    title: this._t('help_shortcuts', 'Keyboard Shortcuts'),
                    icon: '⌨️',
                    content: shortcuts
                });
            }

            // Troubleshooting
            const troubleshooting = this._t(`plugin.${pluginId}.help_troubleshooting`);
            if (troubleshooting && troubleshooting !== `plugin.${pluginId}.help_troubleshooting`) {
                sections.push({
                    id: 'troubleshooting',
                    title: this._t('help_troubleshooting', 'Troubleshooting'),
                    icon: '🔧',
                    content: troubleshooting
                });
            }

            // FAQ
            const faq = this._t(`plugin.${pluginId}.help_faq`);
            if (faq && faq !== `plugin.${pluginId}.help_faq`) {
                sections.push({
                    id: 'faq',
                    title: this._t('help_faq', 'FAQ'),
                    icon: '❓',
                    content: faq
                });
            }

            // If no sections found, add a default
            if (sections.length === 0) {
                sections.push({
                    id: 'default',
                    title: this._t('help_no_content', 'Help'),
                    icon: 'ℹ️',
                    content: this._t('help_no_content_message', 
                        'No help content available for this plugin. Check the documentation for more information.')
                });
            }

            return { sections };
        }

        /**
         * Render help sections
         * @private
         */
        _renderSections(content) {
            if (!this.elements.sections) return;

            const sections = content.sections || [];
            
            this.elements.sections.innerHTML = sections.map(section => `
                <div class="help-section ${this.options.collapsible ? 'collapsible' : ''}" 
                     data-section="${section.id}">
                    <button class="help-section-header" 
                            aria-expanded="true"
                            aria-controls="help-section-${section.id}">
                        <span class="section-icon">${section.icon || '📄'}</span>
                        <span class="section-title">${this._escapeHtml(section.title)}</span>
                        ${this.options.collapsible ? '<span class="section-toggle">▼</span>' : ''}
                    </button>
                    <div class="help-section-content" id="help-section-${section.id}">
                        ${this._renderContent(section.content)}
                    </div>
                </div>
            `).join('');

            // Bind section toggle events
            this.elements.sections.querySelectorAll('.help-section-header').forEach(header => {
                header.addEventListener('click', () => this._toggleSection(header));
            });
        }

        /**
         * Render section content (supports markdown-like formatting)
         * @private
         */
        _renderContent(content) {
            if (!content) return '';

            // If content is an array (steps/items), render as list
            if (Array.isArray(content)) {
                return `<ol class="help-steps">
                    ${content.map(item => `<li>${this._escapeHtml(item)}</li>`).join('')}
                </ol>`;
            }

            // If content is an object (key-value pairs like shortcuts)
            if (typeof content === 'object') {
                return `<dl class="help-definitions">
                    ${Object.entries(content).map(([key, value]) => 
                        `<dt><kbd>${this._escapeHtml(key)}</kbd></dt>
                         <dd>${this._escapeHtml(value)}</dd>`
                    ).join('')}
                </dl>`;
            }

            // String content - basic markdown-like formatting
            let html = this._escapeHtml(content);
            
            // Bold: **text**
            html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
            
            // Italic: *text*
            html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
            
            // Code: `code`
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
            
            // Links: [text](url)
            html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, 
                '<a href="$2" target="_blank" rel="noopener">$1</a>');
            
            // Line breaks
            html = html.replace(/\n/g, '<br>');

            return `<div class="help-text">${html}</div>`;
        }

        /**
         * Toggle section expansion
         * @private
         */
        _toggleSection(header) {
            if (!this.options.collapsible) return;

            const section = header.closest('.help-section');
            const content = section.querySelector('.help-section-content');
            const isExpanded = header.getAttribute('aria-expanded') === 'true';

            header.setAttribute('aria-expanded', !isExpanded);
            content.style.display = isExpanded ? 'none' : '';
            
            const toggle = header.querySelector('.section-toggle');
            if (toggle) {
                toggle.textContent = isExpanded ? '▶' : '▼';
            }
        }

        /**
         * Filter sections by search query
         * @private
         */
        _filterSections(query) {
            if (!this.elements.sections) return;

            const normalizedQuery = query.toLowerCase().trim();
            const sections = this.elements.sections.querySelectorAll('.help-section');

            sections.forEach(section => {
                if (!normalizedQuery) {
                    section.style.display = '';
                    return;
                }

                const title = section.querySelector('.section-title')?.textContent?.toLowerCase() || '';
                const content = section.querySelector('.help-section-content')?.textContent?.toLowerCase() || '';
                
                const matches = title.includes(normalizedQuery) || content.includes(normalizedQuery);
                section.style.display = matches ? '' : 'none';

                // Highlight matches in content
                if (matches && normalizedQuery) {
                    this._highlightMatches(section, normalizedQuery);
                }
            });
        }

        /**
         * Highlight search matches
         * @private
         */
        _highlightMatches(section, query) {
            // Remove existing highlights
            section.querySelectorAll('.help-highlight').forEach(el => {
                el.outerHTML = el.textContent;
            });

            // Add new highlights (simplified - could be improved)
            const content = section.querySelector('.help-section-content');
            if (content) {
                const regex = new RegExp(`(${this._escapeRegex(query)})`, 'gi');
                content.innerHTML = content.innerHTML.replace(regex, '<mark class="help-highlight">$1</mark>');
            }
        }

        /**
         * Toggle panel visibility
         */
        toggle() {
            this.isExpanded = !this.isExpanded;
            
            if (this.element) {
                this.element.classList.toggle('collapsed', !this.isExpanded);
                this.elements.toggleBtn?.setAttribute('aria-expanded', this.isExpanded);
                
                const icon = this.elements.toggleBtn?.querySelector('.icon');
                if (icon) {
                    icon.textContent = this.isExpanded ? '◀' : '▶';
                }
            }
        }

        /**
         * Show/hide loading state
         * @private
         */
        _showLoading(show) {
            if (this.elements.loading) {
                this.elements.loading.style.display = show ? '' : 'none';
            }
            if (this.elements.sections) {
                this.elements.sections.style.display = show ? 'none' : '';
            }
        }

        /**
         * Render error message
         * @private
         */
        _renderError(message) {
            if (!this.elements.sections) return;

            this.elements.sections.innerHTML = `
                <div class="help-error">
                    <span class="icon">⚠️</span>
                    <p>${this._escapeHtml(message)}</p>
                    <button class="btn btn-sm btn-secondary" onclick="this.closest('.help-panel').helpPanel?.retry()">
                        ${this._t('retry', 'Retry')}
                    </button>
                </div>
            `;
        }

        /**
         * Show feedback dialog
         * @private
         */
        _showFeedbackDialog() {
            if (window.jupiterBridge?.modal?.show) {
                window.jupiterBridge.modal.show({
                    title: this._t('feedback_title', 'Send Feedback'),
                    content: `
                        <form class="feedback-form">
                            <div class="form-group">
                                <label for="feedback-type">${this._t('feedback_type', 'Type')}</label>
                                <select id="feedback-type" class="form-control">
                                    <option value="bug">${this._t('feedback_bug', 'Bug Report')}</option>
                                    <option value="feature">${this._t('feedback_feature', 'Feature Request')}</option>
                                    <option value="improvement">${this._t('feedback_improvement', 'Improvement')}</option>
                                    <option value="question">${this._t('feedback_question', 'Question')}</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="feedback-message">${this._t('feedback_message', 'Message')}</label>
                                <textarea id="feedback-message" class="form-control" rows="4" 
                                          placeholder="${this._t('feedback_placeholder', 'Describe your feedback...')}"></textarea>
                            </div>
                        </form>
                    `,
                    buttons: [
                        { label: this._t('cancel', 'Cancel'), action: 'close' },
                        { label: this._t('send', 'Send'), action: 'submit', class: 'btn-primary' }
                    ],
                    onAction: async (action) => {
                        if (action === 'submit') {
                            await this._submitFeedback();
                        }
                    }
                });
            } else {
                alert(this._t('feedback_not_available', 'Feedback form not available'));
            }
        }

        /**
         * Submit feedback
         * @private
         */
        async _submitFeedback() {
            const type = document.getElementById('feedback-type')?.value;
            const message = document.getElementById('feedback-message')?.value;

            if (!message?.trim()) {
                window.jupiterBridge?.notify?.error?.(this._t('feedback_empty', 'Please enter a message'));
                return;
            }

            try {
                await fetch('/api/v1/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type,
                        message,
                        pluginId: this.pluginId,
                        source: 'help-panel'
                    })
                });

                window.jupiterBridge?.notify?.success?.(this._t('feedback_sent', 'Thank you for your feedback!'));
            } catch (error) {
                window.jupiterBridge?.notify?.error?.(this._t('feedback_error', 'Failed to send feedback'));
            }
        }

        /**
         * Retry loading help
         */
        retry() {
            if (this.pluginId) {
                this.loadPluginHelp(this.pluginId);
            }
        }

        /**
         * Translation helper
         * @private
         */
        _t(key, fallback = '') {
            if (this.i18n?.t) {
                const result = this.i18n.t(key);
                return result !== key ? result : fallback;
            }
            return fallback;
        }

        /**
         * Check if an input element is focused
         * @private
         */
        _isInputFocused() {
            const active = document.activeElement;
            return active && (
                active.tagName === 'INPUT' ||
                active.tagName === 'TEXTAREA' ||
                active.isContentEditable
            );
        }

        /**
         * Escape HTML
         * @private
         */
        _escapeHtml(str) {
            if (str === null || str === undefined) return '';
            const div = document.createElement('div');
            div.textContent = String(str);
            return div.innerHTML;
        }

        /**
         * Escape regex special characters
         * @private
         */
        _escapeRegex(str) {
            return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        }

        /**
         * Destroy the panel
         */
        destroy() {
            if (this.element?.parentNode) {
                this.element.parentNode.removeChild(this.element);
            }
            this.element = null;
            this.elements = {};
            this.helpContent = null;
        }
    }

    // =============================================================================
    // FACTORY FUNCTION
    // =============================================================================

    /**
     * Create a help panel
     * @param {string|HTMLElement} container - Container element or selector
     * @param {Object} options - Panel options
     * @returns {HelpPanel}
     */
    function createHelpPanel(container, options = {}) {
        const panel = new HelpPanel(options);
        panel.render(container);
        return panel;
    }

    /**
     * Get version
     */
    function getVersion() {
        return VERSION;
    }

    // =============================================================================
    // PUBLIC API
    // =============================================================================

    const helpPanel = {
        HelpPanel,
        create: createHelpPanel,
        getVersion
    };

    // Export globally
    window.jupiterHelpPanel = helpPanel;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = helpPanel;
    }

})(typeof window !== 'undefined' ? window : this);
