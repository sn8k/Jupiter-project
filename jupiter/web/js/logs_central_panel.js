/**
 * Jupiter Central Logs Panel Component
 * 
 * Version: 0.1.0
 * 
 * Provides a centralized log viewer with multi-plugin filtering,
 * time range selection, and automatic injection into plugin pages.
 * 
 * Features:
 * - Filter by plugin ID
 * - Filter by log level
 * - Filter by time range (last 5m, 15m, 1h, 24h, custom)
 * - Automatic injection into plugin pages
 * - Aggregated view from all plugins
 * - Export filtered logs
 * 
 * @module jupiter/web/js/logs_central_panel
 */

(function(global) {
    'use strict';

    const VERSION = '0.1.0';

    // =============================================================================
    // LOG LEVELS (shared with logs_panel.js)
    // =============================================================================

    const LOG_LEVELS = {
        DEBUG: { value: 10, color: '#888', icon: '🔍' },
        INFO: { value: 20, color: '#4a9eff', icon: 'ℹ️' },
        WARNING: { value: 30, color: '#ffa500', icon: '⚠️' },
        ERROR: { value: 40, color: '#ff4444', icon: '❌' },
        CRITICAL: { value: 50, color: '#ff0000', icon: '🔥' }
    };

    // =============================================================================
    // TIME RANGE PRESETS
    // =============================================================================

    const TIME_RANGES = {
        '5m': { label: 'Last 5 minutes', ms: 5 * 60 * 1000 },
        '15m': { label: 'Last 15 minutes', ms: 15 * 60 * 1000 },
        '1h': { label: 'Last hour', ms: 60 * 60 * 1000 },
        '4h': { label: 'Last 4 hours', ms: 4 * 60 * 60 * 1000 },
        '24h': { label: 'Last 24 hours', ms: 24 * 60 * 60 * 1000 },
        'all': { label: 'All time', ms: Infinity },
        'custom': { label: 'Custom range', ms: 0 }
    };

    // =============================================================================
    // CENTRAL LOGS PANEL CLASS
    // =============================================================================

    class CentralLogsPanel {
        /**
         * @param {Object} options - Configuration options
         * @param {string} [options.apiBase='/api/v1'] - Base URL for API calls
         * @param {string} [options.wsPath='/ws'] - WebSocket path
         * @param {number} [options.maxLogs=5000] - Maximum logs to keep in memory
         * @param {boolean} [options.autoConnect=true] - Auto-connect to WebSocket
         */
        constructor(options = {}) {
            this.options = {
                apiBase: options.apiBase || '/api/v1',
                wsPath: options.wsPath || '/ws',
                maxLogs: options.maxLogs || 5000,
                autoConnect: options.autoConnect !== false,
                defaultTimeRange: options.defaultTimeRange || '1h',
                ...options
            };

            // State
            this.allLogs = [];
            this.filteredLogs = [];
            this.plugins = new Map(); // plugin_id -> { name, enabled }
            this.ws = null;
            this.connected = false;

            // Filters
            this.filters = {
                plugins: new Set(), // Empty = all plugins
                level: 'INFO',
                timeRange: this.options.defaultTimeRange,
                customStart: null,
                customEnd: null,
                searchQuery: ''
            };

            // UI elements
            this.element = null;
            this.logsContainer = null;
            this.collapsed = false;
            
            // Injection tracking
            this._injectedPanels = new Map(); // container -> mini panel
        }

        /**
         * Render the central logs panel
         * @param {string|HTMLElement} container - Container element or selector
         * @returns {HTMLElement} The rendered panel
         */
        render(container = null) {
            const panel = document.createElement('div');
            panel.className = 'central-logs-panel';
            panel.innerHTML = `
                <div class="central-logs-header">
                    <div class="central-logs-title">
                        <button class="btn btn-icon central-logs-toggle" title="Toggle panel">
                            <span class="toggle-icon">📋</span>
                        </button>
                        <h4>Logs Centralisés</h4>
                        <span class="central-logs-badge" title="Unread logs">0</span>
                    </div>
                    <div class="central-logs-filters">
                        <!-- Plugin filter -->
                        <select class="central-logs-plugin-filter" title="Filter by plugin">
                            <option value="">All Plugins</option>
                        </select>
                        
                        <!-- Level filter -->
                        <select class="central-logs-level-filter" title="Filter by level">
                            ${Object.keys(LOG_LEVELS).map(level => 
                                `<option value="${level}" ${level === this.filters.level ? 'selected' : ''}>${level}</option>`
                            ).join('')}
                        </select>
                        
                        <!-- Time range filter -->
                        <select class="central-logs-time-filter" title="Filter by time">
                            ${Object.entries(TIME_RANGES).map(([key, val]) => 
                                `<option value="${key}" ${key === this.filters.timeRange ? 'selected' : ''}>${val.label}</option>`
                            ).join('')}
                        </select>
                        
                        <!-- Search -->
                        <input type="text" class="central-logs-search" placeholder="Search logs..." />
                        
                        <!-- Actions -->
                        <button class="btn btn-icon central-logs-clear" title="Clear logs">🗑️</button>
                        <button class="btn btn-icon central-logs-export" title="Export logs">💾</button>
                    </div>
                </div>
                <div class="central-logs-content">
                    <div class="central-logs-container"></div>
                </div>
                <div class="central-logs-status">
                    <span class="connection-indicator">●</span>
                    <span class="logs-count">0 logs</span>
                    <span class="logs-rate"></span>
                </div>
            `;

            this.element = panel;
            this.logsContainer = panel.querySelector('.central-logs-container');

            this._bindEvents(panel);

            // Append to container
            if (container) {
                if (typeof container === 'string') {
                    container = document.querySelector(container);
                }
                if (container) {
                    container.appendChild(panel);
                }
            }

            // Load available plugins
            this._loadPlugins();

            // Auto-connect
            if (this.options.autoConnect) {
                this.connect();
            }

            return panel;
        }

        /**
         * Bind UI events
         * @private
         */
        _bindEvents(panel) {
            // Toggle collapse
            panel.querySelector('.central-logs-toggle').addEventListener('click', () => {
                this.toggleCollapse();
            });

            // Plugin filter
            panel.querySelector('.central-logs-plugin-filter').addEventListener('change', (e) => {
                if (e.target.value) {
                    this.filters.plugins = new Set([e.target.value]);
                } else {
                    this.filters.plugins.clear();
                }
                this._applyFilters();
            });

            // Level filter
            panel.querySelector('.central-logs-level-filter').addEventListener('change', (e) => {
                this.filters.level = e.target.value;
                this._applyFilters();
            });

            // Time filter
            panel.querySelector('.central-logs-time-filter').addEventListener('change', (e) => {
                this.filters.timeRange = e.target.value;
                if (e.target.value === 'custom') {
                    this._showCustomTimeDialog();
                } else {
                    this._applyFilters();
                }
            });

            // Search
            let searchTimeout;
            panel.querySelector('.central-logs-search').addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.filters.searchQuery = e.target.value.toLowerCase();
                    this._applyFilters();
                }, 300);
            });

            // Clear
            panel.querySelector('.central-logs-clear').addEventListener('click', () => {
                this.clearLogs();
            });

            // Export
            panel.querySelector('.central-logs-export').addEventListener('click', () => {
                this.exportLogs();
            });
        }

        /**
         * Load available plugins from API
         * @private
         */
        async _loadPlugins() {
            try {
                const response = await fetch(`${this.options.apiBase}/plugins/v2`);
                if (response.ok) {
                    const data = await response.json();
                    const plugins = data.plugins || [];
                    
                    const select = this.element.querySelector('.central-logs-plugin-filter');
                    plugins.forEach(plugin => {
                        this.plugins.set(plugin.id, { name: plugin.name, enabled: plugin.enabled });
                        const option = document.createElement('option');
                        option.value = plugin.id;
                        option.textContent = plugin.name || plugin.id;
                        select.appendChild(option);
                    });
                }
            } catch (e) {
                console.warn('[CentralLogsPanel] Failed to load plugins:', e);
            }
        }

        /**
         * Connect to WebSocket for real-time logs
         */
        connect() {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                return;
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}${this.options.wsPath}`;

            try {
                this.ws = new WebSocket(wsUrl);

                this.ws.onopen = () => {
                    this.connected = true;
                    this._updateConnectionStatus(true);
                    console.log('[CentralLogsPanel] WebSocket connected');
                    
                    // Subscribe to logs channel
                    this.ws.send(JSON.stringify({ type: 'subscribe', channel: 'logs' }));
                };

                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        if (data.type === 'log') {
                            this.addLog(data);
                        }
                    } catch (e) {
                        // Ignore non-JSON messages
                    }
                };

                this.ws.onclose = () => {
                    this.connected = false;
                    this._updateConnectionStatus(false);
                    console.log('[CentralLogsPanel] WebSocket disconnected');
                };

                this.ws.onerror = (error) => {
                    console.error('[CentralLogsPanel] WebSocket error:', error);
                };

            } catch (e) {
                console.error('[CentralLogsPanel] Failed to connect:', e);
            }
        }

        /**
         * Disconnect WebSocket
         */
        disconnect() {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
            this.connected = false;
            this._updateConnectionStatus(false);
        }

        /**
         * Update connection status indicator
         * @private
         */
        _updateConnectionStatus(connected) {
            if (!this.element) return;
            const indicator = this.element.querySelector('.connection-indicator');
            if (indicator) {
                indicator.style.color = connected ? '#4caf50' : '#f44336';
                indicator.title = connected ? 'Connected' : 'Disconnected';
            }
        }

        /**
         * Add a log entry
         * @param {Object} log - Log entry
         */
        addLog(log) {
            const entry = this._normalizeLog(log);
            
            this.allLogs.push(entry);
            
            // Enforce max logs
            while (this.allLogs.length > this.options.maxLogs) {
                this.allLogs.shift();
            }

            // Check filters and render if matches
            if (this._matchesFilters(entry)) {
                this.filteredLogs.push(entry);
                this._renderLogEntry(entry);
                this._updateBadge();
            }

            this._updateCount();
        }

        /**
         * Normalize log entry
         * @private
         */
        _normalizeLog(log) {
            return {
                id: log.id || `log-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                timestamp: log.timestamp || log.time || new Date().toISOString(),
                level: (log.level || log.severity || 'INFO').toUpperCase(),
                message: log.message || log.msg || log.text || String(log),
                source: log.source || log.logger || null,
                pluginId: this._extractPluginId(log),
                extra: log.extra || log.metadata || null
            };
        }

        /**
         * Extract plugin ID from log source
         * @private
         */
        _extractPluginId(log) {
            // Try explicit plugin_id
            if (log.plugin_id) return log.plugin_id;
            if (log.pluginId) return log.pluginId;
            
            // Try to extract from source like "[plugin:my_plugin]"
            const source = log.source || log.logger || '';
            const match = source.match(/\[plugin:([a-z][a-z0-9_]*)\]/i);
            if (match) return match[1];
            
            return null;
        }

        /**
         * Check if log matches current filters
         * @private
         */
        _matchesFilters(log) {
            // Plugin filter
            if (this.filters.plugins.size > 0 && log.pluginId) {
                if (!this.filters.plugins.has(log.pluginId)) {
                    return false;
                }
            }

            // Level filter
            const logLevel = LOG_LEVELS[log.level] || LOG_LEVELS.INFO;
            const filterLevel = LOG_LEVELS[this.filters.level] || LOG_LEVELS.DEBUG;
            if (logLevel.value < filterLevel.value) {
                return false;
            }

            // Time range filter
            if (this.filters.timeRange !== 'all') {
                const logTime = new Date(log.timestamp).getTime();
                const now = Date.now();
                
                if (this.filters.timeRange === 'custom') {
                    if (this.filters.customStart && logTime < this.filters.customStart) {
                        return false;
                    }
                    if (this.filters.customEnd && logTime > this.filters.customEnd) {
                        return false;
                    }
                } else {
                    const range = TIME_RANGES[this.filters.timeRange];
                    if (range && now - logTime > range.ms) {
                        return false;
                    }
                }
            }

            // Search query
            if (this.filters.searchQuery) {
                const searchText = `${log.timestamp} ${log.level} ${log.message} ${log.source || ''} ${log.pluginId || ''}`.toLowerCase();
                if (!searchText.includes(this.filters.searchQuery)) {
                    return false;
                }
            }

            return true;
        }

        /**
         * Apply filters and re-render
         * @private
         */
        _applyFilters() {
            this.filteredLogs = this.allLogs.filter(log => this._matchesFilters(log));
            this._renderAllLogs();
        }

        /**
         * Render all filtered logs
         * @private
         */
        _renderAllLogs() {
            if (!this.logsContainer) return;
            
            this.logsContainer.innerHTML = '';
            
            // Only render last 500 for performance
            const logsToRender = this.filteredLogs.slice(-500);
            logsToRender.forEach(log => this._renderLogEntry(log));
            
            this._updateCount();
            this._scrollToBottom();
        }

        /**
         * Render a single log entry
         * @private
         */
        _renderLogEntry(log) {
            if (!this.logsContainer) return;

            const levelInfo = LOG_LEVELS[log.level] || LOG_LEVELS.INFO;
            const time = new Date(log.timestamp).toLocaleTimeString();
            const pluginBadge = log.pluginId 
                ? `<span class="log-plugin-badge">${log.pluginId}</span>` 
                : '';

            const entry = document.createElement('div');
            entry.className = `log-entry log-${log.level.toLowerCase()}`;
            entry.dataset.logId = log.id;
            entry.innerHTML = `
                <span class="log-timestamp">${time}</span>
                <span class="log-level" style="color: ${levelInfo.color}">${levelInfo.icon} ${log.level}</span>
                ${pluginBadge}
                <span class="log-message">${this._escapeHtml(log.message)}</span>
            `;

            this.logsContainer.appendChild(entry);
        }

        /**
         * Update logs count display
         * @private
         */
        _updateCount() {
            if (!this.element) return;
            const countEl = this.element.querySelector('.logs-count');
            if (countEl) {
                countEl.textContent = `${this.filteredLogs.length} / ${this.allLogs.length} logs`;
            }
        }

        /**
         * Update badge with unread count
         * @private
         */
        _updateBadge() {
            if (!this.element || !this.collapsed) return;
            const badge = this.element.querySelector('.central-logs-badge');
            if (badge) {
                const count = parseInt(badge.textContent || '0', 10) + 1;
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            }
        }

        /**
         * Scroll to bottom
         * @private
         */
        _scrollToBottom() {
            if (this.logsContainer) {
                this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
            }
        }

        /**
         * Escape HTML
         * @private
         */
        _escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        /**
         * Toggle collapse state
         */
        toggleCollapse() {
            this.collapsed = !this.collapsed;
            if (this.element) {
                this.element.classList.toggle('collapsed', this.collapsed);
                
                // Reset badge when expanded
                if (!this.collapsed) {
                    const badge = this.element.querySelector('.central-logs-badge');
                    if (badge) {
                        badge.textContent = '0';
                        badge.style.display = 'none';
                    }
                }
            }
        }

        /**
         * Clear all logs
         */
        clearLogs() {
            this.allLogs = [];
            this.filteredLogs = [];
            if (this.logsContainer) {
                this.logsContainer.innerHTML = '';
            }
            this._updateCount();
        }

        /**
         * Export filtered logs
         */
        async exportLogs() {
            const logs = this.filteredLogs.map(log => ({
                timestamp: log.timestamp,
                level: log.level,
                plugin: log.pluginId,
                message: log.message,
                source: log.source
            }));

            const content = JSON.stringify(logs, null, 2);
            const blob = new Blob([content], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `jupiter-logs-${new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')}.json`;
            a.click();
            
            URL.revokeObjectURL(url);
        }

        /**
         * Show custom time range dialog
         * @private
         */
        _showCustomTimeDialog() {
            // Create modal for custom time range
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal" style="max-width: 400px;">
                    <div class="modal-header">
                        <h3>Custom Time Range</h3>
                        <button class="modal-close">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="form-group">
                            <label>Start Time</label>
                            <input type="datetime-local" class="custom-time-start" />
                        </div>
                        <div class="form-group">
                            <label>End Time</label>
                            <input type="datetime-local" class="custom-time-end" />
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary modal-cancel">Cancel</button>
                        <button class="btn btn-primary modal-apply">Apply</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // Set default values
            const now = new Date();
            const hourAgo = new Date(now.getTime() - 60 * 60 * 1000);
            modal.querySelector('.custom-time-start').value = hourAgo.toISOString().slice(0, 16);
            modal.querySelector('.custom-time-end').value = now.toISOString().slice(0, 16);

            // Events
            modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
            modal.querySelector('.modal-cancel').addEventListener('click', () => {
                this.filters.timeRange = '1h';
                if (this.element) {
                    this.element.querySelector('.central-logs-time-filter').value = '1h';
                }
                modal.remove();
            });
            modal.querySelector('.modal-apply').addEventListener('click', () => {
                this.filters.customStart = new Date(modal.querySelector('.custom-time-start').value).getTime();
                this.filters.customEnd = new Date(modal.querySelector('.custom-time-end').value).getTime();
                this._applyFilters();
                modal.remove();
            });
        }

        // =========================================================================
        // INJECTION API - Automatically inject mini logs panel into plugin pages
        // =========================================================================

        /**
         * Inject a mini logs panel into a plugin's page
         * @param {string|HTMLElement} container - Container element or selector
         * @param {string} pluginId - Plugin ID to filter logs for
         * @returns {Object} Mini panel instance
         */
        injectIntoPlugin(container, pluginId) {
            if (typeof container === 'string') {
                container = document.querySelector(container);
            }
            if (!container) {
                console.warn('[CentralLogsPanel] Container not found for injection');
                return null;
            }

            // Don't inject twice
            if (this._injectedPanels.has(container)) {
                return this._injectedPanels.get(container);
            }

            // Create mini panel
            const miniPanel = document.createElement('div');
            miniPanel.className = 'plugin-logs-mini-panel collapsed';
            miniPanel.innerHTML = `
                <div class="mini-logs-header">
                    <button class="btn btn-icon mini-logs-toggle" title="Toggle logs">
                        📋 <span class="mini-logs-badge">0</span>
                    </button>
                    <span class="mini-logs-title">Plugin Logs</span>
                    <div class="mini-logs-controls">
                        <select class="mini-logs-level">
                            ${Object.keys(LOG_LEVELS).map(level => 
                                `<option value="${level}" ${level === 'INFO' ? 'selected' : ''}>${level}</option>`
                            ).join('')}
                        </select>
                        <button class="btn btn-icon mini-logs-clear" title="Clear">🗑️</button>
                    </div>
                </div>
                <div class="mini-logs-content">
                    <div class="mini-logs-container"></div>
                </div>
            `;

            container.appendChild(miniPanel);

            // Create mini panel controller
            const controller = {
                element: miniPanel,
                pluginId: pluginId,
                logs: [],
                levelFilter: 'INFO',
                collapsed: true,
                unread: 0,

                toggle: () => {
                    controller.collapsed = !controller.collapsed;
                    miniPanel.classList.toggle('collapsed', controller.collapsed);
                    if (!controller.collapsed) {
                        controller.unread = 0;
                        miniPanel.querySelector('.mini-logs-badge').textContent = '0';
                    }
                },

                addLog: (log) => {
                    if (log.pluginId !== pluginId) return;
                    
                    const logLevel = LOG_LEVELS[log.level] || LOG_LEVELS.INFO;
                    const filterLevel = LOG_LEVELS[controller.levelFilter] || LOG_LEVELS.DEBUG;
                    if (logLevel.value < filterLevel.value) return;

                    controller.logs.push(log);
                    if (controller.logs.length > 100) {
                        controller.logs.shift();
                    }

                    // Render log
                    const logsContainer = miniPanel.querySelector('.mini-logs-container');
                    const levelInfo = LOG_LEVELS[log.level] || LOG_LEVELS.INFO;
                    const time = new Date(log.timestamp).toLocaleTimeString();
                    
                    const entry = document.createElement('div');
                    entry.className = `log-entry log-${log.level.toLowerCase()}`;
                    entry.innerHTML = `
                        <span class="log-timestamp">${time}</span>
                        <span class="log-level" style="color: ${levelInfo.color}">${log.level}</span>
                        <span class="log-message">${log.message}</span>
                    `;
                    logsContainer.appendChild(entry);
                    logsContainer.scrollTop = logsContainer.scrollHeight;

                    // Update badge if collapsed
                    if (controller.collapsed) {
                        controller.unread++;
                        miniPanel.querySelector('.mini-logs-badge').textContent = 
                            controller.unread > 99 ? '99+' : controller.unread;
                    }
                },

                clear: () => {
                    controller.logs = [];
                    miniPanel.querySelector('.mini-logs-container').innerHTML = '';
                },

                destroy: () => {
                    miniPanel.remove();
                    this._injectedPanels.delete(container);
                }
            };

            // Bind events
            miniPanel.querySelector('.mini-logs-toggle').addEventListener('click', controller.toggle);
            miniPanel.querySelector('.mini-logs-clear').addEventListener('click', controller.clear);
            miniPanel.querySelector('.mini-logs-level').addEventListener('change', (e) => {
                controller.levelFilter = e.target.value;
            });

            // Register for logs
            this._injectedPanels.set(container, controller);

            // Forward existing logs for this plugin
            this.allLogs
                .filter(log => log.pluginId === pluginId)
                .slice(-50)
                .forEach(log => controller.addLog(log));

            return controller;
        }

        /**
         * Remove injected panel from container
         * @param {string|HTMLElement} container - Container element or selector
         */
        removeFromPlugin(container) {
            if (typeof container === 'string') {
                container = document.querySelector(container);
            }
            const controller = this._injectedPanels.get(container);
            if (controller) {
                controller.destroy();
            }
        }

        /**
         * Notify all injected panels about a new log
         * @param {Object} log - Log entry
         */
        _notifyInjectedPanels(log) {
            this._injectedPanels.forEach(controller => {
                controller.addLog(log);
            });
        }

        /**
         * Destroy the panel
         */
        destroy() {
            this.disconnect();
            
            // Remove all injected panels
            this._injectedPanels.forEach(controller => controller.destroy());
            this._injectedPanels.clear();
            
            if (this.element && this.element.parentNode) {
                this.element.parentNode.removeChild(this.element);
            }
            
            this.element = null;
            this.logsContainer = null;
            this.allLogs = [];
            this.filteredLogs = [];
        }
    }

    // =============================================================================
    // SINGLETON INSTANCE
    // =============================================================================

    let centralPanelInstance = null;

    /**
     * Get or create the central logs panel instance
     * @param {Object} [options] - Options for new instance
     * @returns {CentralLogsPanel}
     */
    function getInstance(options = {}) {
        if (!centralPanelInstance) {
            centralPanelInstance = new CentralLogsPanel(options);
        }
        return centralPanelInstance;
    }

    /**
     * Initialize and render the central panel
     * @param {string|HTMLElement} container - Container to render into
     * @param {Object} [options] - Configuration options
     * @returns {CentralLogsPanel}
     */
    function init(container, options = {}) {
        const instance = getInstance(options);
        instance.render(container);
        return instance;
    }

    /**
     * Inject logs panel into a plugin page
     * @param {string|HTMLElement} container - Plugin's container
     * @param {string} pluginId - Plugin ID
     * @returns {Object} Mini panel controller
     */
    function injectIntoPlugin(container, pluginId) {
        const instance = getInstance();
        return instance.injectIntoPlugin(container, pluginId);
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

    const centralLogsPanel = {
        CentralLogsPanel,
        getInstance,
        init,
        injectIntoPlugin,
        getVersion,
        LOG_LEVELS,
        TIME_RANGES
    };

    // Export globally
    global.jupiterCentralLogsPanel = centralLogsPanel;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = centralLogsPanel;
    }

})(typeof window !== 'undefined' ? window : this);
