/**
 * Jupiter Logs Panel Component
 * 
 * Version: 0.2.0
 * 
 * Provides a real-time log viewer with WebSocket streaming,
 * filtering, search, and export capabilities.
 * 
 * Features:
 * - WebSocket connection for real-time logs
 * - Filter by log level (DEBUG, INFO, WARNING, ERROR)
 * - Text search within logs
 * - Pause/resume streaming
 * - Auto-scroll with toggle
 * - Download logs (.log, .txt, .zip)
 * - Tail N last lines
 * - Plugin-specific log filtering
 * - Rate limiting to prevent flooding
 * - Compression for export
 */

(function(global) {
    'use strict';

    const VERSION = '0.2.0';

    // =============================================================================
    // LOG LEVELS
    // =============================================================================

    const LOG_LEVELS = {
        DEBUG: { value: 10, color: '#888', icon: '🔍' },
        INFO: { value: 20, color: '#4a9eff', icon: 'ℹ️' },
        WARNING: { value: 30, color: '#ffa500', icon: '⚠️' },
        ERROR: { value: 40, color: '#ff4444', icon: '❌' },
        CRITICAL: { value: 50, color: '#ff0000', icon: '🔥' }
    };

    const DEFAULT_MAX_LINES = 1000;
    const DEFAULT_TAIL_LINES = 100;
    const DEFAULT_RATE_LIMIT_MS = 50;  // Min time between log entries
    const DEFAULT_BATCH_SIZE = 10;     // Max logs to process per batch

    // =============================================================================
    // LOGS PANEL CLASS
    // =============================================================================

    class LogsPanel {
        constructor(options = {}) {
            this.options = {
                pluginId: options.pluginId || null,
                maxLines: options.maxLines || DEFAULT_MAX_LINES,
                tailLines: options.tailLines || DEFAULT_TAIL_LINES,
                wsPath: options.wsPath || '/ws',
                minLevel: options.minLevel || 'DEBUG',
                autoScroll: options.autoScroll !== false,
                showTimestamp: options.showTimestamp !== false,
                showLevel: options.showLevel !== false,
                showSource: options.showSource !== false,
                containerClass: options.containerClass || 'logs-panel',
                // Rate limiting options
                rateLimitMs: options.rateLimitMs || DEFAULT_RATE_LIMIT_MS,
                batchSize: options.batchSize || DEFAULT_BATCH_SIZE,
                enableRateLimit: options.enableRateLimit !== false,
                // Truncation options
                truncateLongMessages: options.truncateLongMessages !== false,
                maxMessageLength: options.maxMessageLength || 500,
                ...options
            };

            this.logs = [];
            this.filteredLogs = [];
            this.ws = null;
            this.paused = false;
            this.searchQuery = '';
            this.levelFilter = this.options.minLevel;
            this.element = null;
            this.logsContainer = null;
            this.autoScroll = this.options.autoScroll;
            this._reconnectAttempts = 0;
            this._maxReconnectAttempts = 5;
            this._reconnectDelay = 1000;
            
            // Rate limiting state
            this._pendingLogs = [];
            this._lastLogTime = 0;
            this._batchTimeout = null;
            this._logsThisSecond = 0;
            this._lastSecond = 0;
        }

        /**
         * Render the logs panel
         */
        render(container = null) {
            const panel = document.createElement('div');
            panel.className = this.options.containerClass;
            panel.innerHTML = `
                <div class="logs-panel-header">
                    <div class="logs-panel-controls">
                        <select class="logs-level-filter" title="Filter by log level">
                            ${Object.keys(LOG_LEVELS).map(level => 
                                `<option value="${level}" ${level === this.levelFilter ? 'selected' : ''}>${level}</option>`
                            ).join('')}
                        </select>
                        <input type="text" class="logs-search" placeholder="Search logs..." />
                        <button class="btn btn-icon logs-pause" title="Pause/Resume">
                            <span class="logs-pause-icon">⏸️</span>
                        </button>
                        <button class="btn btn-icon logs-autoscroll ${this.autoScroll ? 'active' : ''}" title="Auto-scroll">
                            ⬇️
                        </button>
                        <button class="btn btn-icon logs-clear" title="Clear logs">
                            🗑️
                        </button>
                        <button class="btn btn-icon logs-download" title="Download logs">
                            💾
                        </button>
                    </div>
                    <div class="logs-panel-status">
                        <span class="logs-connection-status">●</span>
                        <span class="logs-count">0 lines</span>
                    </div>
                </div>
                <div class="logs-panel-content">
                    <div class="logs-container"></div>
                </div>
            `;

            this.element = panel;
            this.logsContainer = panel.querySelector('.logs-container');

            // Bind controls
            this._bindControls(panel);

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
         * Bind control events
         * @private
         */
        _bindControls(panel) {
            // Level filter
            const levelSelect = panel.querySelector('.logs-level-filter');
            levelSelect.addEventListener('change', (e) => {
                this.levelFilter = e.target.value;
                this._applyFilters();
            });

            // Search
            const searchInput = panel.querySelector('.logs-search');
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.searchQuery = e.target.value.toLowerCase();
                    this._applyFilters();
                }, 300);
            });

            // Pause/Resume
            const pauseBtn = panel.querySelector('.logs-pause');
            pauseBtn.addEventListener('click', () => {
                this.paused = !this.paused;
                pauseBtn.querySelector('.logs-pause-icon').textContent = this.paused ? '▶️' : '⏸️';
                pauseBtn.title = this.paused ? 'Resume' : 'Pause';
            });

            // Auto-scroll toggle
            const autoScrollBtn = panel.querySelector('.logs-autoscroll');
            autoScrollBtn.addEventListener('click', () => {
                this.autoScroll = !this.autoScroll;
                autoScrollBtn.classList.toggle('active', this.autoScroll);
                if (this.autoScroll) {
                    this._scrollToBottom();
                }
            });

            // Clear
            const clearBtn = panel.querySelector('.logs-clear');
            clearBtn.addEventListener('click', () => {
                this.clear();
            });

            // Download
            const downloadBtn = panel.querySelector('.logs-download');
            downloadBtn.addEventListener('click', () => {
                this.download();
            });

            // Manual scroll detection
            this.logsContainer.addEventListener('scroll', () => {
                const { scrollTop, scrollHeight, clientHeight } = this.logsContainer;
                const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
                this.autoScroll = isAtBottom;
                autoScrollBtn.classList.toggle('active', this.autoScroll);
            });
        }

        /**
         * Connect to WebSocket for live logs
         */
        async connect() {
            return new Promise((resolve, reject) => {
                try {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    let wsUrl = `${protocol}//${window.location.host}`;
                    
                    if (this.options.pluginId) {
                        wsUrl += `/plugins/${this.options.pluginId}/logs/stream`;
                    } else {
                        wsUrl += this.options.wsPath;
                    }

                    this.ws = new WebSocket(wsUrl);

                    this.ws.onopen = () => {
                        console.log('[LogsPanel] WebSocket connected');
                        this._reconnectAttempts = 0;
                        this._updateConnectionStatus(true);
                        resolve();
                    };

                    this.ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            this._handleMessage(data);
                        } catch (e) {
                            // Try as plain text log
                            this.addLog({
                                level: 'INFO',
                                message: event.data,
                                timestamp: new Date().toISOString()
                            });
                        }
                    };

                    this.ws.onclose = () => {
                        console.log('[LogsPanel] WebSocket closed');
                        this._updateConnectionStatus(false);
                        this._scheduleReconnect();
                    };

                    this.ws.onerror = (error) => {
                        console.error('[LogsPanel] WebSocket error:', error);
                        this._updateConnectionStatus(false);
                        reject(error);
                    };

                } catch (e) {
                    reject(e);
                }
            });
        }

        /**
         * Disconnect WebSocket
         */
        disconnect() {
            if (this.ws) {
                this.ws.close();
                this.ws = null;
            }
            this._updateConnectionStatus(false);
        }

        /**
         * Handle incoming WebSocket message
         * @private
         */
        _handleMessage(data) {
            // Handle different message formats
            if (data.type === 'log' || data.log) {
                this.addLog(data.log || data);
            } else if (data.type === 'logs' && Array.isArray(data.logs)) {
                data.logs.forEach(log => this.addLog(log));
            } else if (data.level && data.message) {
                this.addLog(data);
            } else if (data.event === 'log') {
                this.addLog(data.data);
            }
        }

        /**
         * Schedule WebSocket reconnection
         * @private
         */
        _scheduleReconnect() {
            if (this._reconnectAttempts >= this._maxReconnectAttempts) {
                console.error('[LogsPanel] Max reconnect attempts reached');
                return;
            }

            const delay = this._reconnectDelay * Math.pow(2, this._reconnectAttempts);
            this._reconnectAttempts++;

            console.log(`[LogsPanel] Reconnecting in ${delay}ms (attempt ${this._reconnectAttempts})`);
            setTimeout(() => this.connect().catch(() => {}), delay);
        }

        /**
         * Update connection status indicator
         * @private
         */
        _updateConnectionStatus(connected) {
            if (!this.element) return;
            const statusEl = this.element.querySelector('.logs-connection-status');
            if (statusEl) {
                statusEl.style.color = connected ? '#4caf50' : '#f44336';
                statusEl.title = connected ? 'Connected' : 'Disconnected';
            }
        }

        /**
         * Add a log entry with rate limiting
         */
        addLog(log) {
            if (this.paused) return;

            const entry = this._normalizeLog(log);
            
            // Apply rate limiting if enabled
            if (this.options.enableRateLimit) {
                this._pendingLogs.push(entry);
                this._scheduleProcessBatch();
            } else {
                this._processLogEntry(entry);
            }
        }

        /**
         * Schedule batch processing of logs
         * @private
         */
        _scheduleProcessBatch() {
            if (this._batchTimeout) return;
            
            const now = Date.now();
            const timeSinceLastLog = now - this._lastLogTime;
            const delay = Math.max(0, this.options.rateLimitMs - timeSinceLastLog);
            
            this._batchTimeout = setTimeout(() => {
                this._processBatch();
                this._batchTimeout = null;
            }, delay);
        }

        /**
         * Process a batch of pending logs
         * @private
         */
        _processBatch() {
            const batchSize = Math.min(this._pendingLogs.length, this.options.batchSize);
            const batch = this._pendingLogs.splice(0, batchSize);
            
            batch.forEach(entry => this._processLogEntry(entry));
            
            this._lastLogTime = Date.now();
            
            // Schedule next batch if more pending
            if (this._pendingLogs.length > 0) {
                this._scheduleProcessBatch();
            }
            
            // Track logs per second for stats
            const currentSecond = Math.floor(this._lastLogTime / 1000);
            if (currentSecond !== this._lastSecond) {
                this._logsThisSecond = 0;
                this._lastSecond = currentSecond;
            }
            this._logsThisSecond += batchSize;
        }

        /**
         * Process a single log entry (internal)
         * @private
         */
        _processLogEntry(entry) {
            // Truncate long messages if enabled
            if (this.options.truncateLongMessages && 
                entry.message.length > this.options.maxMessageLength) {
                entry.message = entry.message.substring(0, this.options.maxMessageLength) + '... [truncated]';
                entry.truncated = true;
            }
            
            this.logs.push(entry);

            // Enforce max lines
            while (this.logs.length > this.options.maxLines) {
                this.logs.shift();
            }

            // Check if passes filters
            if (this._matchesFilters(entry)) {
                this.filteredLogs.push(entry);
                this._renderLogEntry(entry);
            }

            this._updateCount();
        }

        /**
         * Normalize log entry
         * @private
         */
        _normalizeLog(log) {
            return {
                timestamp: log.timestamp || log.time || new Date().toISOString(),
                level: (log.level || log.severity || 'INFO').toUpperCase(),
                message: log.message || log.msg || log.text || String(log),
                source: log.source || log.logger || log.plugin || null,
                extra: log.extra || log.metadata || null
            };
        }

        /**
         * Check if log matches current filters
         * @private
         */
        _matchesFilters(log) {
            // Level filter
            const logLevel = LOG_LEVELS[log.level] || LOG_LEVELS.INFO;
            const filterLevel = LOG_LEVELS[this.levelFilter] || LOG_LEVELS.DEBUG;
            if (logLevel.value < filterLevel.value) {
                return false;
            }

            // Plugin filter
            if (this.options.pluginId && log.source && 
                !log.source.includes(this.options.pluginId)) {
                return false;
            }

            // Text search
            if (this.searchQuery) {
                const searchText = `${log.timestamp} ${log.level} ${log.message} ${log.source || ''}`.toLowerCase();
                if (!searchText.includes(this.searchQuery)) {
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
            this.filteredLogs = this.logs.filter(log => this._matchesFilters(log));
            this._renderAllLogs();
        }

        /**
         * Render all filtered logs
         * @private
         */
        _renderAllLogs() {
            if (!this.logsContainer) return;

            this.logsContainer.innerHTML = '';
            
            // Only render last N lines for performance
            const logsToRender = this.filteredLogs.slice(-this.options.tailLines);
            logsToRender.forEach(log => this._renderLogEntry(log));

            this._updateCount();
            if (this.autoScroll) {
                this._scrollToBottom();
            }
        }

        /**
         * Render a single log entry
         * @private
         */
        _renderLogEntry(log) {
            if (!this.logsContainer) return;

            const levelInfo = LOG_LEVELS[log.level] || LOG_LEVELS.INFO;
            
            const entry = document.createElement('div');
            entry.className = `log-entry log-${log.level.toLowerCase()}`;
            
            let html = '';
            
            if (this.options.showTimestamp) {
                const time = new Date(log.timestamp).toLocaleTimeString();
                html += `<span class="log-timestamp">${time}</span>`;
            }
            
            if (this.options.showLevel) {
                html += `<span class="log-level" style="color: ${levelInfo.color}">${levelInfo.icon} ${log.level}</span>`;
            }
            
            if (this.options.showSource && log.source) {
                html += `<span class="log-source">[${log.source}]</span>`;
            }
            
            html += `<span class="log-message">${this._escapeHtml(log.message)}</span>`;
            
            entry.innerHTML = html;
            this.logsContainer.appendChild(entry);

            // Enforce visible lines limit
            while (this.logsContainer.children.length > this.options.tailLines) {
                this.logsContainer.removeChild(this.logsContainer.firstChild);
            }

            if (this.autoScroll) {
                this._scrollToBottom();
            }
        }

        /**
         * Scroll to bottom of logs
         * @private
         */
        _scrollToBottom() {
            if (this.logsContainer) {
                this.logsContainer.scrollTop = this.logsContainer.scrollHeight;
            }
        }

        /**
         * Update line count display
         * @private
         */
        _updateCount() {
            if (!this.element) return;
            const countEl = this.element.querySelector('.logs-count');
            if (countEl) {
                countEl.textContent = `${this.filteredLogs.length} / ${this.logs.length} lines`;
            }
        }

        /**
         * Clear all logs
         */
        clear() {
            this.logs = [];
            this.filteredLogs = [];
            if (this.logsContainer) {
                this.logsContainer.innerHTML = '';
            }
            this._updateCount();
        }

        /**
         * Download logs as file
         */
        download(format = 'log') {
            const content = this.filteredLogs
                .map(log => `${log.timestamp} [${log.level}] ${log.source ? `[${log.source}] ` : ''}${log.message}`)
                .join('\n');

            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `jupiter-logs-${new Date().toISOString().slice(0, 10)}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        /**
         * Download logs as ZIP (requires JSZip)
         */
        async downloadZip() {
            const content = this.filteredLogs
                .map(log => `${log.timestamp} [${log.level}] ${log.source ? `[${log.source}] ` : ''}${log.message}`)
                .join('\n');
            
            // Try to use JSZip if available
            if (typeof JSZip !== 'undefined') {
                try {
                    const zip = new JSZip();
                    const filename = `jupiter-logs-${new Date().toISOString().slice(0, 10)}.log`;
                    zip.file(filename, content);
                    
                    const blob = await zip.generateAsync({
                        type: 'blob',
                        compression: 'DEFLATE',
                        compressionOptions: { level: 9 }
                    });
                    
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `jupiter-logs-${new Date().toISOString().slice(0, 10)}.zip`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    return;
                } catch (e) {
                    console.warn('[LogsPanel] JSZip compression failed:', e);
                }
            }
            
            // Fallback: Try native CompressionStream API (if supported)
            if (typeof CompressionStream !== 'undefined') {
                try {
                    const blob = new Blob([content], { type: 'text/plain' });
                    const compressedStream = blob.stream().pipeThrough(new CompressionStream('gzip'));
                    const compressedBlob = await new Response(compressedStream).blob();
                    
                    const url = URL.createObjectURL(compressedBlob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `jupiter-logs-${new Date().toISOString().slice(0, 10)}.log.gz`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                    return;
                } catch (e) {
                    console.warn('[LogsPanel] CompressionStream failed:', e);
                }
            }
            
            // Ultimate fallback: plain text
            console.warn('[LogsPanel] ZIP not available, falling back to .log');
            this.download('log');
        }

        /**
         * Get logs per second rate
         */
        getLogsPerSecond() {
            return this._logsThisSecond;
        }

        /**
         * Get pending logs count (for monitoring rate limiting)
         */
        getPendingCount() {
            return this._pendingLogs.length;
        }

        /**
         * Configure rate limiting at runtime
         */
        setRateLimit(options = {}) {
            if (options.enabled !== undefined) {
                this.options.enableRateLimit = options.enabled;
            }
            if (options.rateLimitMs !== undefined) {
                this.options.rateLimitMs = options.rateLimitMs;
            }
            if (options.batchSize !== undefined) {
                this.options.batchSize = options.batchSize;
            }
        }

        /**
         * Configure truncation at runtime
         */
        setTruncation(options = {}) {
            if (options.enabled !== undefined) {
                this.options.truncateLongMessages = options.enabled;
            }
            if (options.maxLength !== undefined) {
                this.options.maxMessageLength = options.maxLength;
            }
        }

        /**
         * Set minimum log level filter
         */
        setLevel(level) {
            this.levelFilter = level.toUpperCase();
            if (this.element) {
                const select = this.element.querySelector('.logs-level-filter');
                if (select) select.value = this.levelFilter;
            }
            this._applyFilters();
        }

        /**
         * Get current logs
         */
        getLogs() {
            return [...this.filteredLogs];
        }

        /**
         * Get all logs (unfiltered)
         */
        getAllLogs() {
            return [...this.logs];
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
         * Destroy the panel
         */
        destroy() {
            this.disconnect();
            if (this.element && this.element.parentNode) {
                this.element.parentNode.removeChild(this.element);
            }
            this.element = null;
            this.logsContainer = null;
            this.logs = [];
            this.filteredLogs = [];
        }
    }

    // =============================================================================
    // FACTORY FUNCTION
    // =============================================================================

    /**
     * Create a logs panel
     */
    function createLogsPanel(container, options = {}) {
        const panel = new LogsPanel(options);
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

    const logsPanel = {
        LogsPanel,
        create: createLogsPanel,
        getVersion,
        LOG_LEVELS
    };

    // Export globally
    global.jupiterLogsPanel = logsPanel;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = logsPanel;
    }

})(typeof window !== 'undefined' ? window : this);
