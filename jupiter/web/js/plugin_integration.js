/**
 * Plugin Integration Module - Jupiter WebUI
 * 
 * Wires together all plugin frontend modules with the main app.js.
 * This module initializes the plugin system, connects to the backend,
 * and provides the glue code between new modules and existing UI.
 * 
 * @version 0.2.0
 * @module jupiter/web/js/plugin_integration
 */

(function(window) {
    'use strict';

    /**
     * Plugin Integration Manager
     */
    class PluginIntegration {
        constructor() {
            this.initialized = false;
            this.bridge = null;
            this.container = null;
            this.logsPanel = null;
            this.metricsWidget = null;
            this.i18n = null;
            
            // State
            this.plugins = [];
            this.activePlugin = null;
        }

        /**
         * Initialize the plugin integration
         * @param {Object} options - Configuration options
         * @returns {Promise<void>}
         */
        async init(options = {}) {
            if (this.initialized) {
                console.warn('[PluginIntegration] Already initialized');
                return;
            }

            console.log('[PluginIntegration] Initializing...');

            const apiBase = options.apiBase || window.state?.apiBaseUrl || '/api/v1';

            // Initialize i18n first (if available)
            if (window.I18nLoader) {
                this.i18n = window.i18n || new window.I18nLoader({
                    langPath: 'lang',
                    defaultLang: window.state?.i18n?.lang || 'fr'
                });
                // Don't await - let it load in background
                this.i18n.init().catch(e => console.warn('[PluginIntegration] i18n init warning:', e));
            }

            // Initialize Jupiter Bridge
            if (window.JupiterBridge) {
                this.bridge = new window.JupiterBridge({ apiBase });
                await this.bridge.init();
                
                // Subscribe to plugin events
                this.bridge.events.subscribe('PLUGIN_LOADED', (data) => this._onPluginLoaded(data));
                this.bridge.events.subscribe('PLUGIN_ERROR', (data) => this._onPluginError(data));
                this.bridge.events.subscribe('PLUGIN_RELOADED', (data) => this._onPluginReloaded(data));
            }

            // Initialize Plugin Container
            if (window.PluginContainer) {
                this.container = new window.PluginContainer({
                    apiBase,
                    bridge: this.bridge
                });
            }

            // Initialize Metrics Widget (for dashboard)
            if (window.MetricsWidget) {
                const metricsContainer = document.getElementById('plugin-metrics-widget');
                if (metricsContainer) {
                    this.metricsWidget = new window.MetricsWidget({
                        apiBase,
                        refreshInterval: 10000,
                        onThresholdExceeded: (alert) => this._onMetricAlert(alert)
                    });
                    this.metricsWidget.init(metricsContainer);
                }
            }

            // Load plugins list
            await this._loadPlugins();

            // Integrate with existing pluginUIState if available
            this._integrateWithExistingUI();

            this.initialized = true;
            console.log('[PluginIntegration] Initialized successfully');

            // Emit ready event
            window.dispatchEvent(new CustomEvent('jupiter:pluginSystemReady', {
                detail: { plugins: this.plugins }
            }));
        }

        /**
         * Load plugins from API
         * @private
         */
        async _loadPlugins() {
            if (!this.bridge) return;

            try {
                this.plugins = await this.bridge.plugins.list();
                console.log(`[PluginIntegration] Loaded ${this.plugins.length} plugins`);
            } catch (e) {
                console.error('[PluginIntegration] Failed to load plugins:', e);
                this.plugins = [];
            }
        }

        /**
         * Integrate with existing app.js pluginUIState
         * @private
         */
        _integrateWithExistingUI() {
            // Hook into existing navigation
            if (typeof window.pluginUIState !== 'undefined') {
                // Sync loaded plugins
                const pluginsWithUI = this.plugins.filter(p => 
                    p.ui_contribution && p.ui_contribution.panels?.length > 0
                );
                
                // Don't override if already populated
                if (window.pluginUIState.sidebarPlugins.length === 0) {
                    window.pluginUIState.sidebarPlugins = pluginsWithUI.map(p => ({
                        name: p.id,
                        view_id: p.id,
                        menu_icon: p.manifest?.icon || '🔌',
                        menu_label_key: `plugin_${p.id}_name`,
                        menu_order: p.ui_contribution?.menu_order || 100
                    }));
                }
            }

            // Hook into settings view
            this._hookSettingsView();

            // Initialize UX utils integration
            this._integrateUxUtils();
        }

        /**
         * Hook into settings view to show plugin settings
         * @private
         */
        _hookSettingsView() {
            const settingsContainer = document.getElementById('plugin-settings-container');
            if (!settingsContainer) return;

            // Get plugins with settings
            const pluginsWithSettings = this.plugins.filter(p => 
                p.manifest?.settings_schema || p.ui_contribution?.settings_schema
            );

            // Don't add anything if no plugins have settings
            if (pluginsWithSettings.length === 0) {
                settingsContainer.style.display = 'none';
                return;
            }

            settingsContainer.style.display = '';

            // Create header section for plugin settings
            if (!settingsContainer.querySelector('.plugin-settings-header')) {
                const header = document.createElement('section');
                header.className = 'panel settings-section plugin-settings-header';
                header.innerHTML = `
                    <header>
                        <h3 data-i18n="settings_plugins_title">🧩 Plugin Settings</h3>
                        <p class="muted small" data-i18n="settings_plugins_subtitle">Configure individual plugin settings below.</p>
                    </header>
                    <div class="plugin-settings-selector">
                        <label for="plugin-settings-select" data-i18n="settings_plugin_select">Select plugin:</label>
                        <select id="plugin-settings-select">
                            <option value="" data-i18n="settings_plugin_none">-- Select a plugin --</option>
                        </select>
                    </div>
                `;
                settingsContainer.appendChild(header);

                // Populate select
                const select = header.querySelector('#plugin-settings-select');
                pluginsWithSettings.forEach(plugin => {
                    const option = document.createElement('option');
                    option.value = plugin.id;
                    option.textContent = plugin.manifest?.name || plugin.id;
                    select.appendChild(option);
                });

                // Handle selection
                select.addEventListener('change', (e) => {
                    this._showPluginSettings(e.target.value, settingsContainer);
                });
            }

            // Create container for plugin settings frame
            if (!settingsContainer.querySelector('.plugin-settings-frame-wrapper')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'plugin-settings-frame-wrapper';
                wrapper.style.display = 'none';
                settingsContainer.appendChild(wrapper);
            }

            // Initialize PluginSettingsFrame if available
            if (window.PluginSettingsFrame) {
                const wrapper = settingsContainer.querySelector('.plugin-settings-frame-wrapper');
                if (!wrapper.dataset.initialized) {
                    this.settingsFrame = new window.PluginSettingsFrame({
                        apiBase: this.bridge?.apiBase || '/api/v1',
                        autoForm: window.AutoForm ? new window.AutoForm() : null,
                        onSettingsSave: (settings) => {
                            const select = settingsContainer.querySelector('#plugin-settings-select');
                            const pluginId = select?.value;
                            if (pluginId) {
                                console.log(`[PluginIntegration] Settings saved for ${pluginId}`);
                                this._notifySettingsSaved(pluginId, settings);
                            }
                        }
                    });
                    this.settingsFrame.init(wrapper);
                    wrapper.dataset.initialized = 'true';
                }
            }
        }

        /**
         * Show settings for a specific plugin
         * @private
         */
        _showPluginSettings(pluginId, container) {
            const wrapper = container.querySelector('.plugin-settings-frame-wrapper');
            if (!wrapper || !this.settingsFrame) return;

            if (!pluginId) {
                wrapper.style.display = 'none';
                return;
            }

            wrapper.style.display = '';
            this.settingsFrame.loadPlugin(pluginId).catch(e => 
                console.warn(`[PluginIntegration] Could not load settings for ${pluginId}:`, e)
            );
        }

        /**
         * Integrate UX utilities into existing components
         * @private
         */
        _integrateUxUtils() {
            if (!window.jupiterUxUtils) {
                console.log('[PluginIntegration] UX utils not loaded, skipping integration');
                return;
            }

            const ux = window.jupiterUxUtils;

            // Enhance scan progress bars with ux_utils
            this._enhanceScanProgress(ux);

            // Add skeleton loaders to plugin containers
            this._addSkeletonLoaders(ux);

            // Enhance status badges
            this._enhanceStatusBadges(ux);

            console.log('[PluginIntegration] UX utils integrated');
        }

        /**
         * Enhance scan progress indicators
         * @private
         */
        _enhanceScanProgress(ux) {
            // Hook into scan progress updates to use enhanced progress bar
            const originalProgress = document.getElementById('watch-progress-bar');
            if (originalProgress) {
                // Add step progress for scan phases
                const watchPanel = document.getElementById('watch-panel');
                if (watchPanel && !watchPanel.querySelector('.scan-step-progress')) {
                    const stepContainer = document.createElement('div');
                    stepContainer.className = 'scan-step-progress';
                    stepContainer.style.marginBottom = '1rem';
                    stepContainer.style.display = 'none'; // Hidden by default
                    
                    const stepProgress = ux.createStepProgress({
                        steps: ['Initialize', 'Scanning', 'Analyzing', 'Complete'],
                        current: 0
                    });
                    stepContainer.appendChild(stepProgress);
                    
                    // Insert before progress bar
                    const progressDiv = document.getElementById('watch-progress');
                    if (progressDiv) {
                        progressDiv.parentNode.insertBefore(stepContainer, progressDiv);
                    }
                    
                    // Store reference for updates
                    this._scanStepProgress = stepProgress;
                    this._scanStepContainer = stepContainer;
                }
            }
        }

        /**
         * Add skeleton loaders to plugin containers
         * @private
         */
        _addSkeletonLoaders(ux) {
            // Add skeleton to plugin views container when loading
            const pluginViewsContainer = document.getElementById('plugin-views-container');
            if (pluginViewsContainer) {
                const skeleton = document.createElement('div');
                skeleton.id = 'plugin-loading-skeleton';
                skeleton.className = 'plugin-loading-skeleton hidden';
                skeleton.style.padding = '1rem';
                
                // Create a card-like skeleton
                skeleton.appendChild(ux.createSkeleton({ type: 'rectangle', height: '60px' }));
                skeleton.appendChild(document.createElement('br'));
                skeleton.appendChild(ux.createSkeleton({ type: 'text', lines: 3 }));
                skeleton.appendChild(document.createElement('br'));
                skeleton.appendChild(ux.createSkeleton({ type: 'rectangle', height: '200px' }));
                
                pluginViewsContainer.appendChild(skeleton);
            }
        }

        /**
         * Enhance status badges with UX utils
         * @private
         */
        _enhanceStatusBadges(ux) {
            // Create a helper for dynamic badge creation
            window.createJupiterBadge = (status, label) => {
                return ux.createTaskStatus(status, label);
            };
            
            // Provide helper for progress indicators
            window.createJupiterProgress = (options = {}) => {
                if (options.type === 'ring') {
                    return ux.createProgressRing(options);
                } else if (options.type === 'steps') {
                    return ux.createStepProgress(options);
                }
                return ux.createProgressBar(options);
            };
        }

        /**
         * Update scan step progress
         * @param {number} step - Step index (0-3)
         */
        updateScanStep(step) {
            if (this._scanStepProgress) {
                this._scanStepProgress.setStep(step);
            }
            if (this._scanStepContainer) {
                this._scanStepContainer.style.display = step >= 0 && step < 4 ? '' : 'none';
            }
        }

        /**
         * Show loading skeleton for plugins
         * @param {boolean} show - Show or hide
         */
        showPluginLoadingSkeleton(show) {
            const skeleton = document.getElementById('plugin-loading-skeleton');
            if (skeleton) {
                skeleton.classList.toggle('hidden', !show);
            }
        }

        /**
         * Open plugin view
         * @param {string} pluginId - Plugin identifier
         */
        async openPluginView(pluginId) {
            if (!this.container) {
                console.error('[PluginIntegration] Container not initialized');
                return;
            }

            const plugin = this.plugins.find(p => p.id === pluginId);
            if (!plugin) {
                console.error(`[PluginIntegration] Plugin not found: ${pluginId}`);
                return;
            }

            this.activePlugin = pluginId;

            // Find or create container element
            let containerEl = document.querySelector(`section.view[data-view="plugin-${pluginId}"]`);
            if (!containerEl) {
                containerEl = this._createPluginViewSection(pluginId, plugin);
            }

            // Mount plugin panel
            const panelConfig = plugin.ui_contribution?.panels?.[0];
            if (panelConfig) {
                await this.container.mount(containerEl.id || `plugin-view-${pluginId}`, {
                    ...panelConfig,
                    pluginId
                });
            }
        }

        /**
         * Create a plugin view section
         * @private
         */
        _createPluginViewSection(pluginId, plugin) {
            const container = document.getElementById('plugin-views-container') || 
                              document.querySelector('.content');
            if (!container) return null;

            const section = document.createElement('section');
            section.className = 'view hidden';
            section.dataset.view = `plugin-${pluginId}`;
            section.dataset.pluginName = pluginId;
            section.id = `plugin-view-${pluginId}`;
            section.setAttribute('aria-label', `Plugin ${plugin.manifest?.name || pluginId}`);

            container.appendChild(section);
            return section;
        }

        /**
         * Open logs panel for a plugin
         * @param {string} pluginId - Plugin identifier
         * @param {HTMLElement} container - Container element
         */
        openLogsPanel(pluginId, container) {
            if (!window.LogsPanel) {
                console.error('[PluginIntegration] LogsPanel not available');
                return;
            }

            const logsPanel = new window.LogsPanel({
                apiBase: this.bridge?.apiBase || '/api/v1',
                wsPath: `/plugins/${pluginId}/logs/stream`,
                source: pluginId
            });
            logsPanel.init(container);

            return logsPanel;
        }

        /**
         * Show plugin modal
         * @param {Object} options - Modal options
         */
        showModal(options) {
            if (this.bridge) {
                // Use bridge modal if available
                if (this.bridge.modal) {
                    this.bridge.modal.show(options);
                    return;
                }
            }

            // Fallback to simple modal
            this._showFallbackModal(options);
        }

        /**
         * Show fallback modal
         * @private
         */
        _showFallbackModal(options) {
            const { title, content, actions = [] } = options;

            // Create modal overlay
            let overlay = document.getElementById('plugin-modal-overlay');
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'plugin-modal-overlay';
                overlay.className = 'modal-overlay';
                document.body.appendChild(overlay);
            }

            overlay.innerHTML = `
                <div class="modal">
                    <header>
                        <h3>${title || ''}</h3>
                        <button class="ghost small" data-action="close-modal">✕</button>
                    </header>
                    <div class="modal-body">
                        ${typeof content === 'string' ? content : ''}
                    </div>
                    <footer>
                        ${actions.map(a => `
                            <button class="${a.class || 'secondary'}" data-modal-action="${a.id}">
                                ${a.label}
                            </button>
                        `).join('')}
                    </footer>
                </div>
            `;

            // Bind close
            overlay.querySelector('[data-action="close-modal"]')?.addEventListener('click', () => {
                overlay.classList.add('hidden');
            });

            // Bind actions
            actions.forEach(action => {
                const btn = overlay.querySelector(`[data-modal-action="${action.id}"]`);
                if (btn && action.onClick) {
                    btn.addEventListener('click', () => {
                        action.onClick();
                        if (action.closeOnClick !== false) {
                            overlay.classList.add('hidden');
                        }
                    });
                }
            });

            overlay.classList.remove('hidden');

            // Insert content if it's an element
            if (content instanceof HTMLElement) {
                const body = overlay.querySelector('.modal-body');
                body.innerHTML = '';
                body.appendChild(content);
            }
        }

        /**
         * Handle plugin loaded event
         * @private
         */
        _onPluginLoaded(data) {
            console.log('[PluginIntegration] Plugin loaded:', data.plugin_id);
            this._loadPlugins(); // Refresh list
        }

        /**
         * Handle plugin error event
         * @private
         */
        _onPluginError(data) {
            console.error('[PluginIntegration] Plugin error:', data);
            if (this.bridge) {
                this.bridge.notify({
                    type: 'error',
                    message: `Plugin error: ${data.error || data.plugin_id}`
                });
            }
        }

        /**
         * Handle plugin reloaded event
         * @private
         */
        _onPluginReloaded(data) {
            console.log('[PluginIntegration] Plugin reloaded:', data.plugin_id);
            
            // Unmount if currently mounted
            if (this.container && this.activePlugin === data.plugin_id) {
                this.container.unmount(data.plugin_id);
                // Re-mount after a short delay
                setTimeout(() => this.openPluginView(data.plugin_id), 500);
            }

            // Notify
            if (this.bridge) {
                this.bridge.notify({
                    type: 'success',
                    message: `Plugin ${data.plugin_id} reloaded`
                });
            }
        }

        /**
         * Handle metric alert
         * @private
         */
        _onMetricAlert(alert) {
            console.warn('[PluginIntegration] Metric alert:', alert);
            if (this.bridge) {
                this.bridge.notify({
                    type: alert.level === 'critical' ? 'error' : 'warning',
                    message: `${alert.metric}: ${alert.value} (threshold: ${alert.threshold})`
                });
            }
        }

        /**
         * Notify settings saved
         * @private
         */
        _notifySettingsSaved(pluginId, settings) {
            if (this.bridge) {
                this.bridge.events.emit('CONFIG_CHANGED', {
                    plugin_id: pluginId,
                    settings
                });
            }
        }

        /**
         * Get plugin by ID
         * @param {string} pluginId - Plugin identifier
         * @returns {Object|null}
         */
        getPlugin(pluginId) {
            return this.plugins.find(p => p.id === pluginId) || null;
        }

        /**
         * Get all plugins
         * @returns {Array}
         */
        getAllPlugins() {
            return [...this.plugins];
        }

        /**
         * Refresh plugins
         * @returns {Promise<void>}
         */
        async refresh() {
            await this._loadPlugins();
            this._integrateWithExistingUI();
            
            // Reload menus if function exists
            if (typeof window.loadPluginMenus === 'function') {
                await window.loadPluginMenus();
            }
        }

        /**
         * Destroy the integration
         */
        destroy() {
            if (this.metricsWidget) {
                this.metricsWidget.destroy();
            }
            if (this.container) {
                this.container.unmountAll();
            }
            if (this.bridge) {
                this.bridge.disconnect();
            }
            
            this.initialized = false;
            console.log('[PluginIntegration] Destroyed');
        }
    }

    // Create singleton instance
    const pluginIntegration = new PluginIntegration();

    // Export
    window.PluginIntegration = PluginIntegration;
    window.pluginIntegration = pluginIntegration;

    // Auto-initialize when DOM is ready and after app.js init
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            // Wait for app.js to initialize first
            setTimeout(() => {
                if (window.state?.apiBaseUrl) {
                    pluginIntegration.init({ apiBase: window.state.apiBaseUrl });
                }
            }, 100);
        });
    } else {
        // DOM already loaded, wait for state
        setTimeout(() => {
            if (window.state?.apiBaseUrl) {
                pluginIntegration.init({ apiBase: window.state.apiBaseUrl });
            }
        }, 100);
    }

})(window);
