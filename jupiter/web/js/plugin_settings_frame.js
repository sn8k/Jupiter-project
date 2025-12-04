/**
 * Plugin Settings Frame - Jupiter Bridge Frontend
 * 
 * Provides a unified settings UI for plugin configuration.
 * Features:
 * - Dynamic form generation from plugin manifest settings schema
 * - Settings validation and persistence
 * - Live preview of changes
 * - Reset to defaults functionality
 * - Import/Export settings
 * 
 * @version 0.2.0
 * @module jupiter/web/js/plugin_settings_frame
 */

(function(window) {
    'use strict';

    /**
     * Plugin Settings Frame Manager
     */
    class PluginSettingsFrame {
        /**
         * @param {Object} options - Configuration options
         * @param {string} options.apiBase - Base URL for API calls
         * @param {Object} [options.autoForm] - AutoForm instance for form generation
         * @param {boolean} [options.showDebugToggle] - Show debug mode toggle (default: true)
         */
        constructor(options = {}) {
            this.apiBase = options.apiBase || '/api/v1';
            this.autoForm = options.autoForm || (window.AutoForm ? new window.AutoForm() : null);
            
            // State
            this.activePlugin = null;
            this.originalSettings = {};
            this.currentSettings = {};
            this.isDirty = false;
            
            // Options
            this.showDebugToggle = options.showDebugToggle !== false;
            
            // Debug timer interval
            this._debugTimerInterval = null;
            
            // UI elements cache
            this.elements = {};
            
            // Event handlers
            this.onSettingsChange = options.onSettingsChange || null;
            this.onSettingsSave = options.onSettingsSave || null;
        }

        /**
         * Initialize the settings frame
         * @param {string|HTMLElement} container - Container element or selector
         */
        init(container) {
            this.container = typeof container === 'string' 
                ? document.querySelector(container)
                : container;
            
            if (!this.container) {
                console.error('[PluginSettingsFrame] Container not found');
                return;
            }

            this._createUI();
            this._bindEvents();
            
            console.log('[PluginSettingsFrame] Initialized');
        }

        /**
         * Create the settings frame UI
         * @private
         */
        _createUI() {
            this.container.innerHTML = `
                <div class="plugin-settings-frame">
                    <div class="settings-header">
                        <div class="settings-title">
                            <span class="plugin-icon">⚙️</span>
                            <h3 class="plugin-name" data-i18n="plugin_settings_title">Plugin Settings</h3>
                        </div>
                        <div class="settings-actions">
                            <button class="btn btn-sm btn-ghost" data-action="check-update" title="Check for updates">
                                <span class="icon">🔍</span>
                            </button>
                            <button class="btn btn-sm btn-ghost" data-action="view-changelog" title="View changelog">
                                <span class="icon">📋</span>
                            </button>
                            <button class="btn btn-sm btn-ghost" data-action="import" title="Import settings">
                                <span class="icon">📥</span>
                            </button>
                            <button class="btn btn-sm btn-ghost" data-action="export" title="Export settings">
                                <span class="icon">📤</span>
                            </button>
                            <button class="btn btn-sm btn-ghost" data-action="reset" title="Reset to defaults">
                                <span class="icon">🔄</span>
                            </button>
                        </div>
                    </div>
                    
                    <div class="settings-info">
                        <p class="plugin-description"></p>
                        <div class="settings-info-meta">
                            <span class="plugin-version badge"></span>
                            <span class="plugin-update-badge badge badge-success" style="display: none;"></span>
                        </div>
                    </div>
                    
                    <div class="settings-debug-bar" style="display: none;">
                        <label class="toggle-label">
                            <input type="checkbox" class="debug-toggle" data-action="toggle-debug">
                            <span class="toggle-slider"></span>
                            <span data-i18n="debug_mode">Debug Mode</span>
                        </label>
                        <span class="debug-timer"></span>
                    </div>
                    
                    <div class="settings-tabs">
                        <div class="tab-list" role="tablist"></div>
                    </div>
                    
                    <div class="settings-body">
                        <div class="settings-form-container">
                            <!-- Auto-generated form will be inserted here -->
                        </div>
                        <div class="settings-preview" style="display: none;">
                            <h4 data-i18n="settings_preview">Settings Preview</h4>
                            <pre class="settings-json"></pre>
                        </div>
                    </div>
                    
                    <div class="settings-footer">
                        <div class="dirty-indicator" style="display: none;">
                            <span class="icon">⚠️</span>
                            <span data-i18n="unsaved_changes">Unsaved changes</span>
                        </div>
                        <div class="footer-actions">
                            <button class="btn btn-secondary" data-action="cancel" data-i18n="cancel">Cancel</button>
                            <button class="btn btn-primary" data-action="save" data-i18n="save">Save</button>
                        </div>
                    </div>
                </div>
            `;

            // Cache UI elements
            this.elements = {
                frame: this.container.querySelector('.plugin-settings-frame'),
                pluginName: this.container.querySelector('.plugin-name'),
                pluginDescription: this.container.querySelector('.plugin-description'),
                pluginVersion: this.container.querySelector('.plugin-version'),
                updateBadge: this.container.querySelector('.plugin-update-badge'),
                debugBar: this.container.querySelector('.settings-debug-bar'),
                debugToggle: this.container.querySelector('.debug-toggle'),
                debugTimer: this.container.querySelector('.debug-timer'),
                tabList: this.container.querySelector('.tab-list'),
                formContainer: this.container.querySelector('.settings-form-container'),
                preview: this.container.querySelector('.settings-preview'),
                previewJson: this.container.querySelector('.settings-json'),
                dirtyIndicator: this.container.querySelector('.dirty-indicator'),
                saveBtn: this.container.querySelector('[data-action="save"]'),
                cancelBtn: this.container.querySelector('[data-action="cancel"]'),
                importBtn: this.container.querySelector('[data-action="import"]'),
                exportBtn: this.container.querySelector('[data-action="export"]'),
                resetBtn: this.container.querySelector('[data-action="reset"]'),
                checkUpdateBtn: this.container.querySelector('[data-action="check-update"]'),
                viewChangelogBtn: this.container.querySelector('[data-action="view-changelog"]')
            };
        }

        /**
         * Bind event handlers
         * @private
         */
        _bindEvents() {
            // Save button
            this.elements.saveBtn?.addEventListener('click', () => this.save());
            
            // Cancel button
            this.elements.cancelBtn?.addEventListener('click', () => this.cancel());
            
            // Reset button
            this.elements.resetBtn?.addEventListener('click', () => this.resetToDefaults());
            
            // Import button
            this.elements.importBtn?.addEventListener('click', () => this.importSettings());
            
            // Export button
            this.elements.exportBtn?.addEventListener('click', () => this.exportSettings());
            
            // Check update button
            this.elements.checkUpdateBtn?.addEventListener('click', () => this.checkForUpdate());
            
            // View changelog button
            this.elements.viewChangelogBtn?.addEventListener('click', () => this.viewChangelog());
            
            // Debug toggle
            this.elements.debugToggle?.addEventListener('change', (e) => this.toggleDebugMode(e.target.checked));
            
            // Form change listener
            this.elements.formContainer?.addEventListener('change', (e) => {
                this._handleFormChange(e);
            });
            
            // Tab click
            this.elements.tabList?.addEventListener('click', (e) => {
                const tab = e.target.closest('[role="tab"]');
                if (tab) {
                    this._switchTab(tab.dataset.tab);
                }
            });
        }

        /**
         * Load settings for a plugin
         * @param {string} pluginId - Plugin identifier
         * @returns {Promise<Object>} Plugin settings
         */
        async loadPlugin(pluginId) {
            try {
                // Fetch plugin manifest and current settings
                const [manifest, settings] = await Promise.all([
                    this._fetchManifest(pluginId),
                    this._fetchSettings(pluginId)
                ]);
                
                this.activePlugin = {
                    id: pluginId,
                    manifest: manifest,
                    schema: manifest.settings_schema || manifest.settingsSchema || {}
                };
                
                this.originalSettings = JSON.parse(JSON.stringify(settings));
                this.currentSettings = JSON.parse(JSON.stringify(settings));
                this.isDirty = false;
                
                this._renderPluginInfo();
                this._renderTabs();
                this._renderForm();
                this._updateDirtyState();
                
                console.log(`[PluginSettingsFrame] Loaded settings for ${pluginId}`);
                return settings;
                
            } catch (error) {
                console.error(`[PluginSettingsFrame] Failed to load plugin ${pluginId}:`, error);
                this._showError(`Failed to load settings: ${error.message}`);
                throw error;
            }
        }

        /**
         * Fetch plugin manifest
         * @private
         */
        async _fetchManifest(pluginId) {
            const response = await fetch(`${this.apiBase}/plugins/${pluginId}/manifest`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        }

        /**
         * Fetch plugin settings
         * @private
         */
        async _fetchSettings(pluginId) {
            const response = await fetch(`${this.apiBase}/plugins/${pluginId}/settings`);
            if (!response.ok) {
                if (response.status === 404) {
                    return {}; // No settings yet
                }
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        }

        /**
         * Render plugin info header
         * @private
         */
        _renderPluginInfo() {
            if (!this.activePlugin) return;
            
            const manifest = this.activePlugin.manifest;
            
            this.elements.pluginName.textContent = manifest.name || this.activePlugin.id;
            this.elements.pluginDescription.textContent = manifest.description || '';
            this.elements.pluginVersion.textContent = `v${manifest.version || '0.0.0'}`;
            
            // Update icon if available
            const iconSpan = this.container.querySelector('.plugin-icon');
            if (iconSpan && manifest.icon) {
                iconSpan.textContent = manifest.icon;
            }
            
            // Show debug bar if plugin supports it and option is enabled
            const supportsDebug = manifest.capabilities?.debug 
                || manifest.dev_mode 
                || manifest.debug_mode;
            
            if (this.elements.debugBar) {
                this.elements.debugBar.style.display = 
                    (this.showDebugToggle && supportsDebug) ? '' : 'none';
                
                // Check current debug state
                if (supportsDebug) {
                    this._loadDebugState();
                }
            }
            
            // Reset update badge
            if (this.elements.updateBadge) {
                this.elements.updateBadge.style.display = 'none';
            }
        }

        /**
         * Load current debug state from server
         * @private
         */
        async _loadDebugState() {
            if (!this.activePlugin) return;
            
            try {
                const response = await fetch(`${this.apiBase}/plugins/${this.activePlugin.id}/debug`);
                if (response.ok) {
                    const data = await response.json();
                    if (this.elements.debugToggle) {
                        this.elements.debugToggle.checked = data.enabled || false;
                    }
                    if (data.enabled && data.remainingSeconds) {
                        this._startDebugTimer(data.remainingSeconds);
                    }
                }
            } catch (e) {
                // Ignore errors, debug state is optional
            }
        }

        /**
         * Render settings tabs based on schema groups
         * @private
         */
        _renderTabs() {
            const schema = this.activePlugin?.schema || {};
            const groups = this._extractGroups(schema);
            
            if (groups.length <= 1) {
                this.elements.tabList.style.display = 'none';
                return;
            }
            
            this.elements.tabList.style.display = 'flex';
            this.elements.tabList.innerHTML = groups.map((group, index) => `
                <button role="tab" 
                        class="tab-btn ${index === 0 ? 'active' : ''}" 
                        data-tab="${group.id}"
                        aria-selected="${index === 0}">
                    ${group.icon || ''} ${group.label}
                </button>
            `).join('');
        }

        /**
         * Extract groups from schema
         * @private
         */
        _extractGroups(schema) {
            const properties = schema.properties || {};
            const groups = new Map();
            
            // Default group
            groups.set('general', { id: 'general', label: 'General', icon: '⚙️', properties: {} });
            
            for (const [key, prop] of Object.entries(properties)) {
                const groupId = prop['x-group'] || 'general';
                
                if (!groups.has(groupId)) {
                    groups.set(groupId, {
                        id: groupId,
                        label: prop['x-group-label'] || groupId,
                        icon: prop['x-group-icon'] || '',
                        properties: {}
                    });
                }
                
                groups.get(groupId).properties[key] = prop;
            }
            
            return Array.from(groups.values());
        }

        /**
         * Render the settings form
         * @private
         */
        _renderForm() {
            if (!this.autoForm) {
                this._renderFallbackForm();
                return;
            }
            
            const schema = this.activePlugin?.schema || {};
            
            // Use AutoForm to generate form
            this.autoForm.init(this.elements.formContainer, {
                schema: schema,
                data: this.currentSettings,
                onChange: (data) => this._handleFormChange({ detail: data })
            });
        }

        /**
         * Render a simple fallback form when AutoForm is not available
         * @private
         */
        _renderFallbackForm() {
            const schema = this.activePlugin?.schema || {};
            const properties = schema.properties || {};
            
            let html = '<form class="settings-form fallback-form">';
            
            for (const [key, prop] of Object.entries(properties)) {
                const value = this.currentSettings[key] ?? prop.default ?? '';
                const type = prop.type || 'string';
                const required = (schema.required || []).includes(key);
                
                html += `
                    <div class="form-group">
                        <label for="setting-${key}" class="form-label">
                            ${prop.title || key}
                            ${required ? '<span class="required">*</span>' : ''}
                        </label>
                        ${this._renderFallbackInput(key, prop, value)}
                        ${prop.description ? `<p class="form-hint">${prop.description}</p>` : ''}
                    </div>
                `;
            }
            
            html += '</form>';
            this.elements.formContainer.innerHTML = html;
        }

        /**
         * Render a fallback input element
         * @private
         */
        _renderFallbackInput(key, prop, value) {
            const type = prop.type || 'string';
            const id = `setting-${key}`;
            
            switch (type) {
                case 'boolean':
                    return `
                        <label class="toggle">
                            <input type="checkbox" id="${id}" name="${key}" ${value ? 'checked' : ''}>
                            <span class="toggle-slider"></span>
                        </label>
                    `;
                    
                case 'integer':
                case 'number':
                    return `
                        <input type="number" id="${id}" name="${key}" value="${value}"
                               ${prop.minimum !== undefined ? `min="${prop.minimum}"` : ''}
                               ${prop.maximum !== undefined ? `max="${prop.maximum}"` : ''}
                               class="form-control">
                    `;
                    
                case 'array':
                    if (prop.enum) {
                        return `
                            <select id="${id}" name="${key}" multiple class="form-control">
                                ${prop.enum.map(opt => `
                                    <option value="${opt}" ${(value || []).includes(opt) ? 'selected' : ''}>
                                        ${opt}
                                    </option>
                                `).join('')}
                            </select>
                        `;
                    }
                    return `<textarea id="${id}" name="${key}" class="form-control">${JSON.stringify(value || [], null, 2)}</textarea>`;
                    
                default:
                    if (prop.enum) {
                        return `
                            <select id="${id}" name="${key}" class="form-control">
                                ${prop.enum.map(opt => `
                                    <option value="${opt}" ${value === opt ? 'selected' : ''}>
                                        ${opt}
                                    </option>
                                `).join('')}
                            </select>
                        `;
                    }
                    if (prop.format === 'textarea' || (prop.maxLength && prop.maxLength > 100)) {
                        return `<textarea id="${id}" name="${key}" class="form-control">${value}</textarea>`;
                    }
                    return `<input type="text" id="${id}" name="${key}" value="${value}" class="form-control">`;
            }
        }

        /**
         * Handle form changes
         * @private
         */
        _handleFormChange(event) {
            // Collect form data
            if (this.autoForm) {
                this.currentSettings = this.autoForm.getData();
            } else {
                this.currentSettings = this._collectFormData();
            }
            
            // Check if dirty
            this.isDirty = JSON.stringify(this.currentSettings) !== JSON.stringify(this.originalSettings);
            this._updateDirtyState();
            
            // Update preview
            this._updatePreview();
            
            // Callback
            if (this.onSettingsChange) {
                this.onSettingsChange(this.currentSettings, this.isDirty);
            }
        }

        /**
         * Collect form data from fallback form
         * @private
         */
        _collectFormData() {
            const form = this.elements.formContainer.querySelector('form');
            if (!form) return {};
            
            const formData = new FormData(form);
            const data = {};
            const schema = this.activePlugin?.schema || {};
            const properties = schema.properties || {};
            
            for (const [key, prop] of Object.entries(properties)) {
                const type = prop.type || 'string';
                const input = form.querySelector(`[name="${key}"]`);
                
                if (!input) continue;
                
                switch (type) {
                    case 'boolean':
                        data[key] = input.checked;
                        break;
                    case 'integer':
                        data[key] = parseInt(input.value, 10) || 0;
                        break;
                    case 'number':
                        data[key] = parseFloat(input.value) || 0;
                        break;
                    case 'array':
                        if (input.tagName === 'SELECT') {
                            data[key] = Array.from(input.selectedOptions).map(o => o.value);
                        } else {
                            try {
                                data[key] = JSON.parse(input.value);
                            } catch {
                                data[key] = [];
                            }
                        }
                        break;
                    default:
                        data[key] = input.value;
                }
            }
            
            return data;
        }

        /**
         * Update dirty state indicator
         * @private
         */
        _updateDirtyState() {
            if (this.elements.dirtyIndicator) {
                this.elements.dirtyIndicator.style.display = this.isDirty ? 'flex' : 'none';
            }
            
            if (this.elements.saveBtn) {
                this.elements.saveBtn.disabled = !this.isDirty;
            }
        }

        /**
         * Update settings preview
         * @private
         */
        _updatePreview() {
            if (this.elements.previewJson) {
                this.elements.previewJson.textContent = JSON.stringify(this.currentSettings, null, 2);
            }
        }

        /**
         * Switch to a tab
         * @private
         */
        _switchTab(tabId) {
            // Update tab buttons
            this.elements.tabList.querySelectorAll('[role="tab"]').forEach(tab => {
                const isActive = tab.dataset.tab === tabId;
                tab.classList.toggle('active', isActive);
                tab.setAttribute('aria-selected', isActive);
            });
            
            // Show/hide form groups
            const formGroups = this.elements.formContainer.querySelectorAll('[data-group]');
            formGroups.forEach(group => {
                group.style.display = group.dataset.group === tabId ? '' : 'none';
            });
        }

        /**
         * Save settings
         * @returns {Promise<boolean>} Success status
         */
        async save() {
            if (!this.activePlugin || !this.isDirty) {
                return true;
            }
            
            try {
                // Validate settings
                const validation = this._validate();
                if (!validation.valid) {
                    this._showValidationErrors(validation.errors);
                    return false;
                }
                
                // Send to API
                const response = await fetch(
                    `${this.apiBase}/plugins/${this.activePlugin.id}/settings`,
                    {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(this.currentSettings)
                    }
                );
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                // Update state
                this.originalSettings = JSON.parse(JSON.stringify(this.currentSettings));
                this.isDirty = false;
                this._updateDirtyState();
                
                // Callback
                if (this.onSettingsSave) {
                    this.onSettingsSave(this.currentSettings);
                }
                
                this._showSuccess('Settings saved successfully');
                console.log(`[PluginSettingsFrame] Settings saved for ${this.activePlugin.id}`);
                
                return true;
                
            } catch (error) {
                console.error('[PluginSettingsFrame] Save failed:', error);
                this._showError(`Failed to save settings: ${error.message}`);
                return false;
            }
        }

        /**
         * Cancel changes
         */
        cancel() {
            if (this.isDirty) {
                const confirmed = confirm('Discard unsaved changes?');
                if (!confirmed) return;
            }
            
            this.currentSettings = JSON.parse(JSON.stringify(this.originalSettings));
            this.isDirty = false;
            this._renderForm();
            this._updateDirtyState();
        }

        /**
         * Reset to default values
         */
        async resetToDefaults() {
            const confirmed = confirm('Reset all settings to default values?');
            if (!confirmed) return;
            
            const schema = this.activePlugin?.schema || {};
            const properties = schema.properties || {};
            
            const defaults = {};
            for (const [key, prop] of Object.entries(properties)) {
                if (prop.default !== undefined) {
                    defaults[key] = prop.default;
                }
            }
            
            this.currentSettings = defaults;
            this.isDirty = JSON.stringify(this.currentSettings) !== JSON.stringify(this.originalSettings);
            
            this._renderForm();
            this._updateDirtyState();
            this._updatePreview();
        }

        /**
         * Import settings from file
         */
        importSettings() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.json';
            
            input.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                try {
                    const text = await file.text();
                    const imported = JSON.parse(text);
                    
                    // Validate imported settings
                    const validation = this._validate(imported);
                    if (!validation.valid) {
                        this._showValidationErrors(validation.errors);
                        return;
                    }
                    
                    this.currentSettings = imported;
                    this.isDirty = true;
                    
                    this._renderForm();
                    this._updateDirtyState();
                    this._updatePreview();
                    
                    this._showSuccess('Settings imported successfully');
                    
                } catch (error) {
                    this._showError(`Failed to import settings: ${error.message}`);
                }
            });
            
            input.click();
        }

        /**
         * Export settings to file
         */
        exportSettings() {
            if (!this.activePlugin) return;
            
            const blob = new Blob(
                [JSON.stringify(this.currentSettings, null, 2)],
                { type: 'application/json' }
            );
            
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.activePlugin.id}-settings.json`;
            a.click();
            
            URL.revokeObjectURL(url);
        }

        /**
         * Validate settings against schema
         * @private
         */
        _validate(settings = null) {
            const data = settings || this.currentSettings;
            const schema = this.activePlugin?.schema || {};
            const properties = schema.properties || {};
            const required = schema.required || [];
            const errors = [];
            
            // Check required fields
            for (const key of required) {
                if (data[key] === undefined || data[key] === null || data[key] === '') {
                    errors.push({
                        field: key,
                        message: `${properties[key]?.title || key} is required`
                    });
                }
            }
            
            // Type validation
            for (const [key, value] of Object.entries(data)) {
                const prop = properties[key];
                if (!prop) continue;
                
                const type = prop.type || 'string';
                
                switch (type) {
                    case 'integer':
                        if (!Number.isInteger(value)) {
                            errors.push({ field: key, message: `${prop.title || key} must be an integer` });
                        }
                        break;
                    case 'number':
                        if (typeof value !== 'number' || isNaN(value)) {
                            errors.push({ field: key, message: `${prop.title || key} must be a number` });
                        }
                        break;
                    case 'boolean':
                        if (typeof value !== 'boolean') {
                            errors.push({ field: key, message: `${prop.title || key} must be a boolean` });
                        }
                        break;
                    case 'array':
                        if (!Array.isArray(value)) {
                            errors.push({ field: key, message: `${prop.title || key} must be an array` });
                        }
                        break;
                }
                
                // Range validation
                if (prop.minimum !== undefined && value < prop.minimum) {
                    errors.push({ field: key, message: `${prop.title || key} must be >= ${prop.minimum}` });
                }
                if (prop.maximum !== undefined && value > prop.maximum) {
                    errors.push({ field: key, message: `${prop.title || key} must be <= ${prop.maximum}` });
                }
                
                // Enum validation
                if (prop.enum && !prop.enum.includes(value)) {
                    errors.push({ field: key, message: `${prop.title || key} must be one of: ${prop.enum.join(', ')}` });
                }
            }
            
            return {
                valid: errors.length === 0,
                errors: errors
            };
        }

        /**
         * Show validation errors
         * @private
         */
        _showValidationErrors(errors) {
            // Clear previous errors
            this.elements.formContainer.querySelectorAll('.field-error').forEach(el => el.remove());
            this.elements.formContainer.querySelectorAll('.has-error').forEach(el => el.classList.remove('has-error'));
            
            // Show new errors
            errors.forEach(error => {
                const field = this.elements.formContainer.querySelector(`[name="${error.field}"]`);
                if (field) {
                    const group = field.closest('.form-group');
                    if (group) {
                        group.classList.add('has-error');
                        const errorEl = document.createElement('p');
                        errorEl.className = 'field-error text-danger';
                        errorEl.textContent = error.message;
                        group.appendChild(errorEl);
                    }
                }
            });
            
            // Show summary toast
            this._showError(`Please fix ${errors.length} validation error(s)`);
        }

        /**
         * Show error message
         * @private
         */
        _showError(message) {
            if (window.jupiterBridge) {
                window.jupiterBridge.notify({ type: 'error', message });
            } else {
                console.error('[PluginSettingsFrame]', message);
                alert(message);
            }
        }

        /**
         * Show success message
         * @private
         */
        _showSuccess(message) {
            if (window.jupiterBridge) {
                window.jupiterBridge.notify({ type: 'success', message });
            } else {
                console.log('[PluginSettingsFrame]', message);
            }
        }

        /**
         * Check for plugin updates
         */
        async checkForUpdate() {
            if (!this.activePlugin) {
                this._showError('No plugin loaded');
                return;
            }

            const pluginId = this.activePlugin.id;
            
            try {
                // Use jupiterBridge if available
                let result;
                if (window.jupiterBridge?.plugins?.checkUpdate) {
                    result = await window.jupiterBridge.plugins.checkUpdate(pluginId);
                } else {
                    const response = await fetch(`${this.apiBase}/plugins/${pluginId}/check-update`);
                    result = await response.json();
                }
                
                if (result.hasUpdate) {
                    this._showUpdateAvailable(result.latestVersion, result.changelog);
                } else if (result.error) {
                    this._showError(`Update check failed: ${result.error}`);
                } else {
                    this._showSuccess('Plugin is up to date');
                }
                
                return result;
            } catch (error) {
                this._showError(`Failed to check for updates: ${error.message}`);
                return { hasUpdate: false, error: error.message };
            }
        }

        /**
         * Show update available UI
         * @private
         */
        _showUpdateAvailable(newVersion, changelog) {
            if (this.elements.updateBadge) {
                this.elements.updateBadge.style.display = '';
                this.elements.updateBadge.textContent = `Update available: v${newVersion}`;
                this.elements.updateBadge.classList.add('clickable');
                this.elements.updateBadge.onclick = () => this.updatePlugin(newVersion);
            }
            
            this._showSuccess(`Update available: v${newVersion}. Click the badge to update.`);
        }

        /**
         * Update plugin to new version
         */
        async updatePlugin(version = null) {
            if (!this.activePlugin) {
                this._showError('No plugin loaded');
                return;
            }

            const pluginId = this.activePlugin.id;
            
            // Confirm update
            const confirmMsg = version 
                ? `Update ${pluginId} to version ${version}?` 
                : `Update ${pluginId} to latest version?`;
            
            if (!confirm(confirmMsg)) {
                return { cancelled: true };
            }
            
            try {
                // Use jupiterBridge if available
                let result;
                if (window.jupiterBridge?.plugins?.update) {
                    result = await window.jupiterBridge.plugins.update(pluginId, version);
                } else {
                    const response = await fetch(`${this.apiBase}/plugins/${pluginId}/update`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ version })
                    });
                    result = await response.json();
                }
                
                if (result.success) {
                    this._showSuccess(`Plugin updated successfully to v${result.version}`);
                    // Refresh plugin info
                    await this.loadPlugin(pluginId);
                } else {
                    this._showError(`Update failed: ${result.error || 'Unknown error'}`);
                }
                
                return result;
            } catch (error) {
                this._showError(`Failed to update plugin: ${error.message}`);
                return { success: false, error: error.message };
            }
        }

        /**
         * View plugin changelog
         */
        async viewChangelog() {
            if (!this.activePlugin) {
                this._showError('No plugin loaded');
                return;
            }

            const pluginId = this.activePlugin.id;
            
            try {
                const response = await fetch(`${this.apiBase}/plugins/${pluginId}/changelog`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        this._showError('No changelog available for this plugin');
                        return;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                const changelog = data.content || data.changelog || 'No changelog content';
                
                // Show in modal
                this._showChangelogModal(pluginId, changelog);
            } catch (error) {
                this._showError(`Failed to load changelog: ${error.message}`);
            }
        }

        /**
         * Show changelog in modal
         * @private
         */
        _showChangelogModal(pluginId, content) {
            // Use jupiterBridge modal if available
            if (window.jupiterBridge?.modal?.show) {
                window.jupiterBridge.modal.show({
                    title: `Changelog: ${pluginId}`,
                    content: `<pre class="changelog-content">${this._escapeHtml(content)}</pre>`,
                    size: 'large',
                    buttons: [
                        { label: 'Close', action: 'close', class: 'btn-primary' }
                    ]
                });
                return;
            }
            
            // Fallback to simple modal
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg">
                    <div class="modal-header">
                        <h3>Changelog: ${pluginId}</h3>
                        <button class="modal-close" aria-label="Close">×</button>
                    </div>
                    <div class="modal-body">
                        <pre class="changelog-content">${this._escapeHtml(content)}</pre>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary">Close</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Close handlers
            modal.querySelector('.modal-close').onclick = () => modal.remove();
            modal.querySelector('.modal-footer button').onclick = () => modal.remove();
            modal.onclick = (e) => {
                if (e.target === modal) modal.remove();
            };
        }

        /**
         * Toggle debug mode for plugin
         * @param {boolean} enabled - Enable or disable debug mode
         */
        async toggleDebugMode(enabled) {
            if (!this.activePlugin) return;

            const pluginId = this.activePlugin.id;
            
            try {
                const response = await fetch(`${this.apiBase}/plugins/${pluginId}/debug`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this._showSuccess(enabled ? 'Debug mode enabled' : 'Debug mode disabled');
                    
                    // Start timer if debug mode enabled with auto-disable
                    if (enabled && result.autoDisableAfter) {
                        this._startDebugTimer(result.autoDisableAfter);
                    } else {
                        this._clearDebugTimer();
                    }
                } else {
                    this._showError(`Failed to toggle debug mode: ${result.error}`);
                    // Revert checkbox
                    if (this.elements.debugToggle) {
                        this.elements.debugToggle.checked = !enabled;
                    }
                }
            } catch (error) {
                this._showError(`Failed to toggle debug mode: ${error.message}`);
                if (this.elements.debugToggle) {
                    this.elements.debugToggle.checked = !enabled;
                }
            }
        }

        /**
         * Start debug auto-disable timer
         * @private
         */
        _startDebugTimer(seconds) {
            this._clearDebugTimer();
            
            let remaining = seconds;
            
            const updateTimer = () => {
                if (this.elements.debugTimer) {
                    const mins = Math.floor(remaining / 60);
                    const secs = remaining % 60;
                    this.elements.debugTimer.textContent = `Auto-disable in ${mins}:${secs.toString().padStart(2, '0')}`;
                }
                
                remaining--;
                
                if (remaining < 0) {
                    this._clearDebugTimer();
                    // Auto-disable
                    if (this.elements.debugToggle) {
                        this.elements.debugToggle.checked = false;
                    }
                    this._showSuccess('Debug mode auto-disabled');
                }
            };
            
            updateTimer();
            this._debugTimerInterval = setInterval(updateTimer, 1000);
        }

        /**
         * Clear debug timer
         * @private
         */
        _clearDebugTimer() {
            if (this._debugTimerInterval) {
                clearInterval(this._debugTimerInterval);
                this._debugTimerInterval = null;
            }
            if (this.elements.debugTimer) {
                this.elements.debugTimer.textContent = '';
            }
        }

        /**
         * Escape HTML to prevent XSS
         * @private
         */
        _escapeHtml(str) {
            if (str === null || str === undefined) return '';
            const div = document.createElement('div');
            div.textContent = String(str);
            return div.innerHTML;
        }

        /**
         * Toggle preview panel
         */
        togglePreview() {
            const preview = this.elements.preview;
            if (preview) {
                const isVisible = preview.style.display !== 'none';
                preview.style.display = isVisible ? 'none' : '';
                this._updatePreview();
            }
        }

        /**
         * Get current settings
         * @returns {Object} Current settings data
         */
        getSettings() {
            return JSON.parse(JSON.stringify(this.currentSettings));
        }

        /**
         * Check if there are unsaved changes
         * @returns {boolean} Dirty state
         */
        hasUnsavedChanges() {
            return this.isDirty;
        }

        /**
         * Destroy the settings frame
         */
        destroy() {
            if (this.autoForm && this.autoForm.destroy) {
                this.autoForm.destroy();
            }
            
            this.container.innerHTML = '';
            this.elements = {};
            this.activePlugin = null;
            this.currentSettings = {};
            this.originalSettings = {};
        }
    }

    // Export to window
    window.PluginSettingsFrame = PluginSettingsFrame;

})(window);
