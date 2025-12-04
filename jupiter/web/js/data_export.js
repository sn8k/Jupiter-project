/**
 * Data Export - Jupiter Bridge Frontend
 * 
 * Provides data export capabilities for AI agents and external tools.
 * Follows the pylance analyzer model for structured exports.
 * 
 * Features:
 * - JSON structured exports with documented schema
 * - Multiple export formats (JSON, NDJSON, CSV)
 * - Size estimation and preview
 * - Streaming for large datasets
 * - Filter and selection support
 * - Export to file or clipboard
 * 
 * @version 0.1.0
 * @module jupiter/web/js/data_export
 */

(function(window) {
    'use strict';

    const VERSION = '0.1.0';

    // =============================================================================
    // EXPORT FORMATS
    // =============================================================================

    const EXPORT_FORMATS = {
        JSON: {
            id: 'json',
            name: 'JSON',
            extension: '.json',
            mimeType: 'application/json',
            description: 'Structured JSON format'
        },
        NDJSON: {
            id: 'ndjson',
            name: 'NDJSON',
            extension: '.ndjson',
            mimeType: 'application/x-ndjson',
            description: 'Newline-delimited JSON (streaming)'
        },
        CSV: {
            id: 'csv',
            name: 'CSV',
            extension: '.csv',
            mimeType: 'text/csv',
            description: 'Comma-separated values'
        },
        MARKDOWN: {
            id: 'markdown',
            name: 'Markdown',
            extension: '.md',
            mimeType: 'text/markdown',
            description: 'Markdown table format'
        }
    };

    // =============================================================================
    // DATA EXPORTER CLASS
    // =============================================================================

    /**
     * Data Exporter Component
     */
    class DataExporter {
        /**
         * @param {Object} options - Configuration options
         * @param {string} [options.apiBase='/api/v1'] - Base URL for API calls
         * @param {number} [options.previewLimit=100] - Max items in preview
         * @param {number} [options.chunkSize=1000] - Chunk size for streaming
         */
        constructor(options = {}) {
            this.options = {
                apiBase: options.apiBase || '/api/v1',
                previewLimit: options.previewLimit || 100,
                chunkSize: options.chunkSize || 1000,
                ...options
            };

            this.element = null;
            this.currentData = null;
            this.selectedFormat = EXPORT_FORMATS.JSON;
            this.filters = {};
            this.selectedFields = null; // null = all fields
        }

        /**
         * Render the export UI
         * @param {string|HTMLElement} container - Container element or selector
         * @returns {HTMLElement}
         */
        render(container) {
            const panel = document.createElement('div');
            panel.className = 'data-export-panel';

            panel.innerHTML = `
                <div class="export-header">
                    <h4 class="export-title">
                        <span class="icon">📤</span>
                        <span data-i18n="export_data">Export Data</span>
                    </h4>
                </div>

                <div class="export-body">
                    <!-- Source Selection -->
                    <div class="export-section">
                        <label class="export-label" data-i18n="export_source">Data Source</label>
                        <select class="form-control export-source-select">
                            <option value="scan">Scan Results</option>
                            <option value="analysis">Analysis Data</option>
                            <option value="functions">Functions</option>
                            <option value="files">Files</option>
                            <option value="metrics">Metrics</option>
                            <option value="history">History</option>
                            <option value="custom">Custom Endpoint</option>
                        </select>
                        <input type="text" class="form-control export-custom-endpoint" 
                               placeholder="/api/v1/custom/endpoint" 
                               style="display: none; margin-top: 8px;">
                    </div>

                    <!-- Format Selection -->
                    <div class="export-section">
                        <label class="export-label" data-i18n="export_format">Format</label>
                        <div class="export-format-options">
                            ${Object.values(EXPORT_FORMATS).map(fmt => `
                                <label class="export-format-option ${fmt.id === 'json' ? 'selected' : ''}">
                                    <input type="radio" name="export-format" value="${fmt.id}" 
                                           ${fmt.id === 'json' ? 'checked' : ''}>
                                    <span class="format-name">${fmt.name}</span>
                                    <span class="format-desc">${fmt.description}</span>
                                </label>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Field Selection -->
                    <div class="export-section">
                        <label class="export-label">
                            <span data-i18n="export_fields">Fields</span>
                            <button class="btn btn-xs btn-link export-select-all" data-i18n="select_all">Select All</button>
                        </label>
                        <div class="export-fields-list">
                            <!-- Populated dynamically -->
                            <p class="text-muted" data-i18n="export_load_preview">Load preview to see available fields</p>
                        </div>
                    </div>

                    <!-- Filters -->
                    <div class="export-section">
                        <label class="export-label" data-i18n="export_filters">Filters</label>
                        <div class="export-filters">
                            <div class="filter-row">
                                <input type="text" class="form-control filter-key" placeholder="Field name">
                                <select class="form-control filter-operator">
                                    <option value="eq">=</option>
                                    <option value="ne">≠</option>
                                    <option value="gt">&gt;</option>
                                    <option value="lt">&lt;</option>
                                    <option value="contains">contains</option>
                                    <option value="startswith">starts with</option>
                                </select>
                                <input type="text" class="form-control filter-value" placeholder="Value">
                                <button class="btn btn-sm btn-ghost filter-add">+</button>
                            </div>
                            <div class="active-filters"></div>
                        </div>
                    </div>

                    <!-- Preview -->
                    <div class="export-section">
                        <div class="export-preview-header">
                            <label class="export-label" data-i18n="export_preview">Preview</label>
                            <button class="btn btn-sm btn-secondary export-load-preview">
                                <span class="icon">🔄</span>
                                <span data-i18n="load_preview">Load Preview</span>
                            </button>
                        </div>
                        <div class="export-preview">
                            <div class="preview-placeholder" data-i18n="export_preview_placeholder">
                                Click "Load Preview" to see data
                            </div>
                            <div class="preview-content" style="display: none;">
                                <pre class="preview-data"></pre>
                            </div>
                        </div>
                        <div class="export-stats">
                            <span class="stat-item">
                                <span class="stat-label" data-i18n="export_items">Items:</span>
                                <span class="stat-value export-item-count">-</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-label" data-i18n="export_size">Est. Size:</span>
                                <span class="stat-value export-size-estimate">-</span>
                            </span>
                        </div>
                    </div>
                </div>

                <div class="export-footer">
                    <button class="btn btn-secondary export-copy">
                        <span class="icon">📋</span>
                        <span data-i18n="copy_to_clipboard">Copy to Clipboard</span>
                    </button>
                    <button class="btn btn-primary export-download">
                        <span class="icon">💾</span>
                        <span data-i18n="download_file">Download File</span>
                    </button>
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
                sourceSelect: this.element.querySelector('.export-source-select'),
                customEndpoint: this.element.querySelector('.export-custom-endpoint'),
                formatOptions: this.element.querySelectorAll('.export-format-option'),
                fieldsList: this.element.querySelector('.export-fields-list'),
                selectAllBtn: this.element.querySelector('.export-select-all'),
                filterKey: this.element.querySelector('.filter-key'),
                filterOperator: this.element.querySelector('.filter-operator'),
                filterValue: this.element.querySelector('.filter-value'),
                filterAdd: this.element.querySelector('.filter-add'),
                activeFilters: this.element.querySelector('.active-filters'),
                loadPreviewBtn: this.element.querySelector('.export-load-preview'),
                previewPlaceholder: this.element.querySelector('.preview-placeholder'),
                previewContent: this.element.querySelector('.preview-content'),
                previewData: this.element.querySelector('.preview-data'),
                itemCount: this.element.querySelector('.export-item-count'),
                sizeEstimate: this.element.querySelector('.export-size-estimate'),
                copyBtn: this.element.querySelector('.export-copy'),
                downloadBtn: this.element.querySelector('.export-download')
            };
        }

        /**
         * Bind event handlers
         * @private
         */
        _bindEvents() {
            // Source selection
            this.elements.sourceSelect?.addEventListener('change', (e) => {
                const isCustom = e.target.value === 'custom';
                this.elements.customEndpoint.style.display = isCustom ? '' : 'none';
                this._resetPreview();
            });

            // Format selection
            this.elements.formatOptions?.forEach(option => {
                option.addEventListener('click', () => {
                    this.elements.formatOptions.forEach(o => o.classList.remove('selected'));
                    option.classList.add('selected');
                    const radio = option.querySelector('input[type="radio"]');
                    if (radio) {
                        radio.checked = true;
                        this.selectedFormat = EXPORT_FORMATS[radio.value.toUpperCase()];
                    }
                    this._updatePreviewFormat();
                });
            });

            // Add filter
            this.elements.filterAdd?.addEventListener('click', () => this._addFilter());

            // Load preview
            this.elements.loadPreviewBtn?.addEventListener('click', () => this.loadPreview());

            // Select all fields
            this.elements.selectAllBtn?.addEventListener('click', () => this._selectAllFields());

            // Copy to clipboard
            this.elements.copyBtn?.addEventListener('click', () => this.copyToClipboard());

            // Download file
            this.elements.downloadBtn?.addEventListener('click', () => this.downloadFile());
        }

        /**
         * Get the current data source endpoint
         * @private
         */
        _getEndpoint() {
            const source = this.elements.sourceSelect?.value || 'scan';
            
            if (source === 'custom') {
                return this.elements.customEndpoint?.value || '';
            }

            const endpoints = {
                scan: '/scan/last',
                analysis: '/analyze/last',
                functions: '/functions',
                files: '/files',
                metrics: '/metrics',
                history: '/snapshots'
            };

            return `${this.options.apiBase}${endpoints[source] || endpoints.scan}`;
        }

        /**
         * Load preview data
         */
        async loadPreview() {
            const endpoint = this._getEndpoint();
            if (!endpoint) {
                this._showError('Please specify an endpoint');
                return;
            }

            this.elements.loadPreviewBtn.disabled = true;
            this.elements.loadPreviewBtn.innerHTML = '<span class="spinner"></span> Loading...';

            try {
                const response = await fetch(endpoint);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const data = await response.json();
                this.currentData = data;

                // Update fields list
                this._populateFields(data);

                // Update preview
                this._updatePreview(data);

                // Update stats
                this._updateStats(data);

            } catch (error) {
                this._showError(`Failed to load data: ${error.message}`);
            } finally {
                this.elements.loadPreviewBtn.disabled = false;
                this.elements.loadPreviewBtn.innerHTML = '<span class="icon">🔄</span> Load Preview';
            }
        }

        /**
         * Populate fields list from data
         * @private
         */
        _populateFields(data) {
            const fields = this._extractFields(data);
            
            this.elements.fieldsList.innerHTML = fields.map(field => `
                <label class="field-checkbox">
                    <input type="checkbox" value="${field}" checked>
                    <span>${field}</span>
                </label>
            `).join('');

            // Bind field checkboxes
            this.elements.fieldsList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.addEventListener('change', () => this._updatePreviewFormat());
            });
        }

        /**
         * Extract field names from data
         * @private
         */
        _extractFields(data) {
            const fields = new Set();

            const extract = (obj, prefix = '') => {
                if (typeof obj !== 'object' || obj === null) return;
                
                if (Array.isArray(obj)) {
                    if (obj.length > 0) {
                        extract(obj[0], prefix);
                    }
                    return;
                }

                for (const [key, value] of Object.entries(obj)) {
                    const fieldName = prefix ? `${prefix}.${key}` : key;
                    fields.add(fieldName);
                    
                    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                        extract(value, fieldName);
                    }
                }
            };

            extract(data);
            return Array.from(fields).sort();
        }

        /**
         * Get selected fields
         * @private
         */
        _getSelectedFields() {
            const checkboxes = this.elements.fieldsList.querySelectorAll('input[type="checkbox"]:checked');
            if (checkboxes.length === 0) return null;
            return Array.from(checkboxes).map(cb => cb.value);
        }

        /**
         * Select all fields
         * @private
         */
        _selectAllFields() {
            this.elements.fieldsList.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                cb.checked = true;
            });
            this._updatePreviewFormat();
        }

        /**
         * Add a filter
         * @private
         */
        _addFilter() {
            const key = this.elements.filterKey?.value?.trim();
            const operator = this.elements.filterOperator?.value;
            const value = this.elements.filterValue?.value?.trim();

            if (!key || !value) return;

            const filterId = `filter-${Date.now()}`;
            this.filters[filterId] = { key, operator, value };

            const filterEl = document.createElement('span');
            filterEl.className = 'filter-tag';
            filterEl.innerHTML = `
                ${key} ${operator} "${value}"
                <button class="filter-remove" data-filter="${filterId}">×</button>
            `;

            filterEl.querySelector('.filter-remove').addEventListener('click', () => {
                delete this.filters[filterId];
                filterEl.remove();
                this._updatePreviewFormat();
            });

            this.elements.activeFilters.appendChild(filterEl);

            // Clear inputs
            this.elements.filterKey.value = '';
            this.elements.filterValue.value = '';

            this._updatePreviewFormat();
        }

        /**
         * Apply filters to data
         * @private
         */
        _applyFilters(data) {
            if (Object.keys(this.filters).length === 0) return data;

            const filterFn = (item) => {
                for (const filter of Object.values(this.filters)) {
                    const value = this._getNestedValue(item, filter.key);
                    if (!this._matchesFilter(value, filter.operator, filter.value)) {
                        return false;
                    }
                }
                return true;
            };

            if (Array.isArray(data)) {
                return data.filter(filterFn);
            }

            // For objects, filter array properties
            const result = { ...data };
            for (const [key, value] of Object.entries(result)) {
                if (Array.isArray(value)) {
                    result[key] = value.filter(filterFn);
                }
            }
            return result;
        }

        /**
         * Check if value matches filter
         * @private
         */
        _matchesFilter(value, operator, filterValue) {
            const strValue = String(value).toLowerCase();
            const strFilter = String(filterValue).toLowerCase();

            switch (operator) {
                case 'eq': return strValue === strFilter;
                case 'ne': return strValue !== strFilter;
                case 'gt': return Number(value) > Number(filterValue);
                case 'lt': return Number(value) < Number(filterValue);
                case 'contains': return strValue.includes(strFilter);
                case 'startswith': return strValue.startsWith(strFilter);
                default: return true;
            }
        }

        /**
         * Get nested value from object
         * @private
         */
        _getNestedValue(obj, path) {
            return path.split('.').reduce((o, k) => o?.[k], obj);
        }

        /**
         * Update preview with formatted data
         * @private
         */
        _updatePreview(data) {
            this.elements.previewPlaceholder.style.display = 'none';
            this.elements.previewContent.style.display = '';
            this._updatePreviewFormat();
        }

        /**
         * Update preview format
         * @private
         */
        _updatePreviewFormat() {
            if (!this.currentData) return;

            const filteredData = this._applyFilters(this.currentData);
            const selectedFields = this._getSelectedFields();
            const projectedData = selectedFields 
                ? this._projectFields(filteredData, selectedFields)
                : filteredData;

            // Limit preview
            const previewData = this._limitData(projectedData, this.options.previewLimit);
            
            // Format based on selected format
            let formatted;
            switch (this.selectedFormat.id) {
                case 'ndjson':
                    formatted = this._formatNDJSON(previewData);
                    break;
                case 'csv':
                    formatted = this._formatCSV(previewData);
                    break;
                case 'markdown':
                    formatted = this._formatMarkdown(previewData);
                    break;
                default:
                    formatted = JSON.stringify(previewData, null, 2);
            }

            this.elements.previewData.textContent = formatted;
            this._updateStats(filteredData);
        }

        /**
         * Project specific fields from data
         * @private
         */
        _projectFields(data, fields) {
            const project = (item) => {
                if (typeof item !== 'object' || item === null) return item;
                
                const result = {};
                for (const field of fields) {
                    const value = this._getNestedValue(item, field);
                    if (value !== undefined) {
                        this._setNestedValue(result, field, value);
                    }
                }
                return result;
            };

            if (Array.isArray(data)) {
                return data.map(project);
            }

            return project(data);
        }

        /**
         * Set nested value in object
         * @private
         */
        _setNestedValue(obj, path, value) {
            const parts = path.split('.');
            let current = obj;
            
            for (let i = 0; i < parts.length - 1; i++) {
                if (!current[parts[i]]) {
                    current[parts[i]] = {};
                }
                current = current[parts[i]];
            }
            
            current[parts[parts.length - 1]] = value;
        }

        /**
         * Limit data for preview
         * @private
         */
        _limitData(data, limit) {
            if (Array.isArray(data)) {
                return data.slice(0, limit);
            }
            return data;
        }

        /**
         * Format as NDJSON
         * @private
         */
        _formatNDJSON(data) {
            if (Array.isArray(data)) {
                return data.map(item => JSON.stringify(item)).join('\n');
            }
            return JSON.stringify(data);
        }

        /**
         * Format as CSV
         * @private
         */
        _formatCSV(data) {
            const items = Array.isArray(data) ? data : [data];
            if (items.length === 0) return '';

            const fields = this._extractFields(items[0]);
            const flatFields = fields.filter(f => !f.includes('.'));

            const header = flatFields.join(',');
            const rows = items.map(item => 
                flatFields.map(field => {
                    const value = item[field];
                    if (value === null || value === undefined) return '';
                    if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                        return `"${value.replace(/"/g, '""')}"`;
                    }
                    return String(value);
                }).join(',')
            );

            return [header, ...rows].join('\n');
        }

        /**
         * Format as Markdown table
         * @private
         */
        _formatMarkdown(data) {
            const items = Array.isArray(data) ? data : [data];
            if (items.length === 0) return '';

            const fields = this._extractFields(items[0]);
            const flatFields = fields.filter(f => !f.includes('.')).slice(0, 10); // Limit columns

            const header = `| ${flatFields.join(' | ')} |`;
            const separator = `| ${flatFields.map(() => '---').join(' | ')} |`;
            const rows = items.map(item => 
                `| ${flatFields.map(field => {
                    const value = item[field];
                    if (value === null || value === undefined) return '';
                    return String(value).replace(/\|/g, '\\|').substring(0, 50);
                }).join(' | ')} |`
            );

            return [header, separator, ...rows].join('\n');
        }

        /**
         * Update statistics
         * @private
         */
        _updateStats(data) {
            // Count items
            let count = 1;
            if (Array.isArray(data)) {
                count = data.length;
            } else if (typeof data === 'object' && data !== null) {
                // Find first array property for count
                for (const value of Object.values(data)) {
                    if (Array.isArray(value)) {
                        count = value.length;
                        break;
                    }
                }
            }

            this.elements.itemCount.textContent = count.toLocaleString();

            // Estimate size
            const jsonStr = JSON.stringify(data);
            const bytes = new Blob([jsonStr]).size;
            this.elements.sizeEstimate.textContent = this._formatBytes(bytes);
        }

        /**
         * Format bytes to human readable
         * @private
         */
        _formatBytes(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        /**
         * Reset preview
         * @private
         */
        _resetPreview() {
            this.currentData = null;
            this.elements.previewPlaceholder.style.display = '';
            this.elements.previewContent.style.display = 'none';
            this.elements.previewData.textContent = '';
            this.elements.fieldsList.innerHTML = '<p class="text-muted">Load preview to see available fields</p>';
            this.elements.itemCount.textContent = '-';
            this.elements.sizeEstimate.textContent = '-';
        }

        /**
         * Show error message
         * @private
         */
        _showError(message) {
            if (window.jupiterBridge?.notify?.error) {
                window.jupiterBridge.notify.error(message);
            } else {
                alert(message);
            }
        }

        /**
         * Get export data
         */
        getExportData() {
            if (!this.currentData) return null;

            const filteredData = this._applyFilters(this.currentData);
            const selectedFields = this._getSelectedFields();
            return selectedFields 
                ? this._projectFields(filteredData, selectedFields)
                : filteredData;
        }

        /**
         * Get formatted export content
         */
        getFormattedContent() {
            const data = this.getExportData();
            if (!data) return '';

            switch (this.selectedFormat.id) {
                case 'ndjson':
                    return this._formatNDJSON(data);
                case 'csv':
                    return this._formatCSV(data);
                case 'markdown':
                    return this._formatMarkdown(data);
                default:
                    return JSON.stringify(data, null, 2);
            }
        }

        /**
         * Copy to clipboard
         */
        async copyToClipboard() {
            const content = this.getFormattedContent();
            if (!content) {
                this._showError('No data to copy. Load preview first.');
                return;
            }

            try {
                await navigator.clipboard.writeText(content);
                if (window.jupiterBridge?.notify?.success) {
                    window.jupiterBridge.notify.success('Copied to clipboard');
                }
            } catch (error) {
                this._showError('Failed to copy to clipboard');
            }
        }

        /**
         * Download as file
         */
        downloadFile() {
            const content = this.getFormattedContent();
            if (!content) {
                this._showError('No data to download. Load preview first.');
                return;
            }

            const source = this.elements.sourceSelect?.value || 'export';
            const filename = `jupiter-${source}-${new Date().toISOString().slice(0, 10)}${this.selectedFormat.extension}`;

            const blob = new Blob([content], { type: this.selectedFormat.mimeType });
            const url = URL.createObjectURL(blob);

            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        /**
         * Destroy the component
         */
        destroy() {
            if (this.element?.parentNode) {
                this.element.parentNode.removeChild(this.element);
            }
            this.element = null;
            this.elements = {};
            this.currentData = null;
        }
    }

    // =============================================================================
    // FACTORY FUNCTION
    // =============================================================================

    /**
     * Create a data exporter
     */
    function createDataExporter(container, options = {}) {
        const exporter = new DataExporter(options);
        exporter.render(container);
        return exporter;
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

    const dataExport = {
        DataExporter,
        EXPORT_FORMATS,
        create: createDataExporter,
        getVersion
    };

    // Export globally
    window.jupiterDataExport = dataExport;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = dataExport;
    }

})(typeof window !== 'undefined' ? window : this);
