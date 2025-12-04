/**
 * Metrics Widget - Jupiter Bridge Frontend
 * 
 * Real-time metrics dashboard widget for plugin performance monitoring.
 * Features:
 * - Live metrics display with auto-refresh
 * - Multiple visualization formats (numbers, charts, gauges)
 * - Configurable thresholds and alerts
 * - Historical data with mini charts
 * - Plugin-specific and system-wide metrics
 * 
 * @version 0.1.0
 * @module jupiter/web/js/metrics_widget
 */

(function(window) {
    'use strict';

    /**
     * Metrics Widget for Jupiter
     */
    class MetricsWidget {
        /**
         * @param {Object} options - Configuration options
         * @param {string} [options.apiBase='/api/v1'] - Base URL for API calls
         * @param {number} [options.refreshInterval=5000] - Auto-refresh interval in ms
         * @param {boolean} [options.autoRefresh=true] - Enable auto-refresh
         */
        constructor(options = {}) {
            this.apiBase = options.apiBase || '/api/v1';
            this.refreshInterval = options.refreshInterval || 5000;
            this.autoRefresh = options.autoRefresh !== false;
            
            // State
            this.metrics = {};
            this.history = new Map(); // key -> array of {timestamp, value}
            this.historyMaxLength = 60; // Keep last 60 data points
            this.refreshTimer = null;
            this.container = null;
            
            // Thresholds for alerts
            this.thresholds = {
                cpu_usage: { warning: 70, critical: 90 },
                memory_usage: { warning: 70, critical: 90 },
                error_rate: { warning: 1, critical: 5 },
                latency_p99: { warning: 500, critical: 1000 }
            };
            
            // Event callbacks
            this.onMetricsUpdate = options.onMetricsUpdate || null;
            this.onThresholdExceeded = options.onThresholdExceeded || null;
        }

        /**
         * Initialize the widget
         * @param {string|HTMLElement} container - Container element or selector
         */
        init(container) {
            this.container = typeof container === 'string'
                ? document.querySelector(container)
                : container;
            
            if (!this.container) {
                console.error('[MetricsWidget] Container not found');
                return;
            }
            
            this._createUI();
            this._bindEvents();
            
            // Initial fetch
            this.refresh();
            
            // Start auto-refresh
            if (this.autoRefresh) {
                this.startAutoRefresh();
            }
            
            console.log('[MetricsWidget] Initialized');
        }

        /**
         * Create the widget UI
         * @private
         */
        _createUI() {
            this.container.innerHTML = `
                <div class="metrics-widget">
                    <div class="metrics-header">
                        <h4 class="metrics-title">
                            <span class="icon">📊</span>
                            <span data-i18n="metrics_title">System Metrics</span>
                        </h4>
                        <div class="metrics-controls">
                            <select class="metrics-scope form-control form-control-sm">
                                <option value="system" data-i18n="metrics_system">System</option>
                                <option value="plugins" data-i18n="metrics_plugins">All Plugins</option>
                            </select>
                            <button class="btn btn-sm btn-ghost metrics-refresh" title="Refresh">
                                <span class="icon">🔄</span>
                            </button>
                            <label class="toggle-sm">
                                <input type="checkbox" class="metrics-auto-refresh" ${this.autoRefresh ? 'checked' : ''}>
                                <span class="toggle-label" data-i18n="auto_refresh">Auto</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="metrics-grid">
                        <!-- Metrics cards will be inserted here -->
                    </div>
                    
                    <div class="metrics-charts">
                        <div class="chart-container" data-metric="requests_per_second">
                            <div class="chart-header">
                                <span data-i18n="requests_per_second">Requests/sec</span>
                            </div>
                            <canvas class="mini-chart"></canvas>
                        </div>
                        <div class="chart-container" data-metric="latency_p50">
                            <div class="chart-header">
                                <span data-i18n="latency">Latency (ms)</span>
                            </div>
                            <canvas class="mini-chart"></canvas>
                        </div>
                    </div>
                    
                    <div class="metrics-footer">
                        <span class="last-updated" data-i18n="last_updated">Last updated:</span>
                        <span class="last-updated-time">-</span>
                    </div>
                </div>
            `;
            
            // Cache elements
            this.elements = {
                grid: this.container.querySelector('.metrics-grid'),
                charts: this.container.querySelector('.metrics-charts'),
                scopeSelect: this.container.querySelector('.metrics-scope'),
                refreshBtn: this.container.querySelector('.metrics-refresh'),
                autoRefreshCheckbox: this.container.querySelector('.metrics-auto-refresh'),
                lastUpdated: this.container.querySelector('.last-updated-time')
            };
        }

        /**
         * Bind event handlers
         * @private
         */
        _bindEvents() {
            // Manual refresh
            this.elements.refreshBtn?.addEventListener('click', () => {
                this.refresh();
            });
            
            // Scope change
            this.elements.scopeSelect?.addEventListener('change', () => {
                this.refresh();
            });
            
            // Auto-refresh toggle
            this.elements.autoRefreshCheckbox?.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        /**
         * Start auto-refresh
         */
        startAutoRefresh() {
            this.stopAutoRefresh();
            this.autoRefresh = true;
            this.refreshTimer = setInterval(() => this.refresh(), this.refreshInterval);
            console.log('[MetricsWidget] Auto-refresh started');
        }

        /**
         * Stop auto-refresh
         */
        stopAutoRefresh() {
            if (this.refreshTimer) {
                clearInterval(this.refreshTimer);
                this.refreshTimer = null;
            }
            this.autoRefresh = false;
            console.log('[MetricsWidget] Auto-refresh stopped');
        }

        /**
         * Refresh metrics data
         * @returns {Promise<Object>}
         */
        async refresh() {
            try {
                const scope = this.elements.scopeSelect?.value || 'system';
                const endpoint = scope === 'plugins' 
                    ? `${this.apiBase}/plugins/metrics`
                    : `${this.apiBase}/metrics`;
                
                const response = await fetch(endpoint);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                this.metrics = data;
                
                // Update history
                this._updateHistory(data);
                
                // Render
                this._renderMetrics();
                this._renderCharts();
                this._updateLastUpdated();
                
                // Check thresholds
                this._checkThresholds(data);
                
                // Callback
                if (this.onMetricsUpdate) {
                    this.onMetricsUpdate(data);
                }
                
                return data;
                
            } catch (error) {
                console.error('[MetricsWidget] Failed to fetch metrics:', error);
                this._showError('Failed to fetch metrics');
                return null;
            }
        }

        /**
         * Update metrics history
         * @private
         */
        _updateHistory(data) {
            const timestamp = Date.now();
            
            const recordMetric = (key, value) => {
                if (typeof value !== 'number') return;
                
                if (!this.history.has(key)) {
                    this.history.set(key, []);
                }
                
                const history = this.history.get(key);
                history.push({ timestamp, value });
                
                // Trim to max length
                while (history.length > this.historyMaxLength) {
                    history.shift();
                }
            };
            
            // Record key metrics
            if (data.counters) {
                for (const [key, value] of Object.entries(data.counters)) {
                    recordMetric(`counter_${key}`, value);
                }
            }
            
            if (data.gauges) {
                for (const [key, value] of Object.entries(data.gauges)) {
                    recordMetric(`gauge_${key}`, value);
                }
            }
            
            // Flatten nested metrics
            const flatMetrics = this._flattenMetrics(data);
            for (const [key, value] of Object.entries(flatMetrics)) {
                recordMetric(key, value);
            }
        }

        /**
         * Flatten nested metrics object
         * @private
         */
        _flattenMetrics(obj, prefix = '') {
            const result = {};
            
            for (const [key, value] of Object.entries(obj)) {
                const newKey = prefix ? `${prefix}_${key}` : key;
                
                if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                    Object.assign(result, this._flattenMetrics(value, newKey));
                } else if (typeof value === 'number') {
                    result[newKey] = value;
                }
            }
            
            return result;
        }

        /**
         * Render metrics cards
         * @private
         */
        _renderMetrics() {
            if (!this.elements.grid) return;
            
            const metrics = this._flattenMetrics(this.metrics);
            const cards = [];
            
            // Priority metrics to show
            const priorityMetrics = [
                { key: 'plugins_loaded', label: 'Plugins Loaded', icon: '🔌', format: 'number' },
                { key: 'plugins_active', label: 'Active Plugins', icon: '✅', format: 'number' },
                { key: 'total_requests', label: 'Total Requests', icon: '📨', format: 'number' },
                { key: 'requests_per_second', label: 'Requests/sec', icon: '⚡', format: 'decimal' },
                { key: 'cpu_usage', label: 'CPU Usage', icon: '💻', format: 'percent' },
                { key: 'memory_usage', label: 'Memory', icon: '🧠', format: 'bytes' },
                { key: 'latency_p50', label: 'Latency P50', icon: '⏱️', format: 'ms' },
                { key: 'latency_p99', label: 'Latency P99', icon: '⏱️', format: 'ms' },
                { key: 'error_count', label: 'Errors', icon: '❌', format: 'number' },
                { key: 'uptime', label: 'Uptime', icon: '🕐', format: 'duration' }
            ];
            
            for (const metric of priorityMetrics) {
                let value = this._findMetricValue(metrics, metric.key);
                if (value === undefined) continue;
                
                const formatted = this._formatValue(value, metric.format);
                const status = this._getMetricStatus(metric.key, value);
                const trend = this._calculateTrend(metric.key);
                
                cards.push(`
                    <div class="metric-card ${status}">
                        <div class="metric-icon">${metric.icon}</div>
                        <div class="metric-content">
                            <div class="metric-value">
                                ${formatted}
                                ${trend ? `<span class="metric-trend ${trend.direction}">${trend.icon}</span>` : ''}
                            </div>
                            <div class="metric-label" data-i18n="${metric.key}">${metric.label}</div>
                        </div>
                    </div>
                `);
            }
            
            this.elements.grid.innerHTML = cards.join('');
        }

        /**
         * Find a metric value with flexible key matching
         * @private
         */
        _findMetricValue(metrics, key) {
            // Direct match
            if (metrics[key] !== undefined) return metrics[key];
            
            // Try common prefixes
            for (const prefix of ['gauge_', 'counter_', 'histogram_']) {
                if (metrics[prefix + key] !== undefined) {
                    return metrics[prefix + key];
                }
            }
            
            // Try case variations
            const lowerKey = key.toLowerCase();
            for (const [k, v] of Object.entries(metrics)) {
                if (k.toLowerCase() === lowerKey) {
                    return v;
                }
            }
            
            return undefined;
        }

        /**
         * Format a value based on type
         * @private
         */
        _formatValue(value, format) {
            switch (format) {
                case 'percent':
                    return `${value.toFixed(1)}%`;
                case 'decimal':
                    return value.toFixed(2);
                case 'bytes':
                    return this._formatBytes(value);
                case 'ms':
                    return `${value.toFixed(0)}ms`;
                case 'duration':
                    return this._formatDuration(value);
                case 'number':
                default:
                    return this._formatNumber(value);
            }
        }

        /**
         * Format bytes to human readable
         * @private
         */
        _formatBytes(bytes) {
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let value = bytes;
            let unitIndex = 0;
            
            while (value >= 1024 && unitIndex < units.length - 1) {
                value /= 1024;
                unitIndex++;
            }
            
            return `${value.toFixed(1)} ${units[unitIndex]}`;
        }

        /**
         * Format duration (seconds to human readable)
         * @private
         */
        _formatDuration(seconds) {
            if (seconds < 60) return `${seconds}s`;
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
            return `${Math.floor(seconds / 86400)}d`;
        }

        /**
         * Format large numbers with suffixes
         * @private
         */
        _formatNumber(value) {
            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
            if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
            return value.toFixed(0);
        }

        /**
         * Get metric status based on thresholds
         * @private
         */
        _getMetricStatus(key, value) {
            const threshold = this.thresholds[key];
            if (!threshold) return '';
            
            if (value >= threshold.critical) return 'critical';
            if (value >= threshold.warning) return 'warning';
            return 'normal';
        }

        /**
         * Calculate trend for a metric
         * @private
         */
        _calculateTrend(key) {
            const history = this.history.get(key) || this.history.get(`gauge_${key}`);
            if (!history || history.length < 2) return null;
            
            const recent = history.slice(-5);
            const first = recent[0].value;
            const last = recent[recent.length - 1].value;
            const diff = last - first;
            
            if (Math.abs(diff) < 0.01) return null;
            
            return {
                direction: diff > 0 ? 'up' : 'down',
                icon: diff > 0 ? '↑' : '↓',
                percent: ((diff / first) * 100).toFixed(1)
            };
        }

        /**
         * Render mini charts
         * @private
         */
        _renderCharts() {
            const chartContainers = this.container.querySelectorAll('.chart-container');
            
            chartContainers.forEach(container => {
                const metricKey = container.dataset.metric;
                const canvas = container.querySelector('.mini-chart');
                
                if (!canvas) return;
                
                // Find history data
                let history = this.history.get(metricKey) || 
                             this.history.get(`gauge_${metricKey}`) ||
                             this.history.get(`counter_${metricKey}`);
                
                if (!history || history.length < 2) {
                    this._drawEmptyChart(canvas);
                    return;
                }
                
                this._drawSparkline(canvas, history);
            });
        }

        /**
         * Draw a sparkline chart
         * @private
         */
        _drawSparkline(canvas, data) {
            const ctx = canvas.getContext('2d');
            const width = canvas.width = canvas.parentElement.clientWidth - 20;
            const height = canvas.height = 40;
            
            ctx.clearRect(0, 0, width, height);
            
            const values = data.map(d => d.value);
            const min = Math.min(...values);
            const max = Math.max(...values);
            const range = max - min || 1;
            
            const padding = 2;
            const chartWidth = width - 2 * padding;
            const chartHeight = height - 2 * padding;
            
            ctx.beginPath();
            ctx.strokeStyle = getComputedStyle(document.documentElement)
                .getPropertyValue('--color-primary') || '#4f9eff';
            ctx.lineWidth = 1.5;
            ctx.lineJoin = 'round';
            
            values.forEach((value, index) => {
                const x = padding + (index / (values.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((value - min) / range) * chartHeight;
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
            
            // Fill gradient
            ctx.lineTo(padding + chartWidth, padding + chartHeight);
            ctx.lineTo(padding, padding + chartHeight);
            ctx.closePath();
            
            const gradient = ctx.createLinearGradient(0, 0, 0, height);
            gradient.addColorStop(0, 'rgba(79, 158, 255, 0.3)');
            gradient.addColorStop(1, 'rgba(79, 158, 255, 0)');
            ctx.fillStyle = gradient;
            ctx.fill();
        }

        /**
         * Draw empty chart placeholder
         * @private
         */
        _drawEmptyChart(canvas) {
            const ctx = canvas.getContext('2d');
            const width = canvas.width = canvas.parentElement.clientWidth - 20;
            const height = canvas.height = 40;
            
            ctx.clearRect(0, 0, width, height);
            ctx.strokeStyle = '#444';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.beginPath();
            ctx.moveTo(0, height / 2);
            ctx.lineTo(width, height / 2);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        /**
         * Check thresholds and emit alerts
         * @private
         */
        _checkThresholds(data) {
            const flatMetrics = this._flattenMetrics(data);
            
            for (const [key, threshold] of Object.entries(this.thresholds)) {
                const value = this._findMetricValue(flatMetrics, key);
                if (value === undefined) continue;
                
                let level = null;
                if (value >= threshold.critical) {
                    level = 'critical';
                } else if (value >= threshold.warning) {
                    level = 'warning';
                }
                
                if (level && this.onThresholdExceeded) {
                    this.onThresholdExceeded({
                        metric: key,
                        value: value,
                        threshold: level === 'critical' ? threshold.critical : threshold.warning,
                        level: level
                    });
                }
            }
        }

        /**
         * Update last updated timestamp
         * @private
         */
        _updateLastUpdated() {
            if (this.elements.lastUpdated) {
                const now = new Date();
                this.elements.lastUpdated.textContent = now.toLocaleTimeString();
            }
        }

        /**
         * Show error message
         * @private
         */
        _showError(message) {
            if (window.jupiterBridge) {
                window.jupiterBridge.notify({ type: 'error', message });
            } else {
                console.error('[MetricsWidget]', message);
            }
        }

        /**
         * Set custom thresholds
         * @param {string} metric - Metric name
         * @param {Object} threshold - {warning: number, critical: number}
         */
        setThreshold(metric, threshold) {
            this.thresholds[metric] = threshold;
        }

        /**
         * Get current metrics
         * @returns {Object}
         */
        getMetrics() {
            return JSON.parse(JSON.stringify(this.metrics));
        }

        /**
         * Get metric history
         * @param {string} key - Metric key
         * @returns {Array}
         */
        getHistory(key) {
            return this.history.get(key) || [];
        }

        /**
         * Destroy the widget
         */
        destroy() {
            this.stopAutoRefresh();
            this.container.innerHTML = '';
            this.history.clear();
            this.metrics = {};
        }
    }

    // Export to window
    window.MetricsWidget = MetricsWidget;

})(window);
