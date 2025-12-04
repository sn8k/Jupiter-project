/**
 * Jupiter Bridge - Frontend API for Plugin Development
 * 
 * Version: 0.1.0
 * 
 * Provides a unified API for plugins to interact with Jupiter's
 * frontend and backend services. Exposed as window.jupiterBridge.
 * 
 * Features:
 * - API calls with authentication
 * - WebSocket connections
 * - Event pub/sub system
 * - i18n translations
 * - Notifications
 * - Modal dialogs
 * - Plugin configuration
 * - AI context export
 */

(function(global) {
    'use strict';

    const VERSION = '0.1.0';

    // =============================================================================
    // INTERNAL STATE
    // =============================================================================

    const bridgeState = {
        initialized: false,
        apiBaseUrl: '',
        token: null,
        ws: null,
        wsReconnectAttempts: 0,
        wsMaxReconnectAttempts: 5,
        wsReconnectDelay: 1000,
        eventSubscriptions: new Map(),  // topic -> Set<callback>
        pendingRequests: new Map(),     // requestId -> {resolve, reject, timeout}
        requestIdCounter: 0
    };

    // =============================================================================
    // API MODULE
    // =============================================================================

    const api = {
        /**
         * Make a GET request
         */
        async get(path, options = {}) {
            return this.request('GET', path, null, options);
        },

        /**
         * Make a POST request
         */
        async post(path, data = null, options = {}) {
            return this.request('POST', path, data, options);
        },

        /**
         * Make a PUT request
         */
        async put(path, data = null, options = {}) {
            return this.request('PUT', path, data, options);
        },

        /**
         * Make a PATCH request
         */
        async patch(path, data = null, options = {}) {
            return this.request('PATCH', path, data, options);
        },

        /**
         * Make a DELETE request
         */
        async delete(path, options = {}) {
            return this.request('DELETE', path, null, options);
        },

        /**
         * Generic request method
         */
        async request(method, path, data = null, options = {}) {
            const url = path.startsWith('http') 
                ? path 
                : `${bridgeState.apiBaseUrl}${path.startsWith('/') ? path : '/' + path}`;

            const headers = new Headers({
                'Content-Type': 'application/json',
                'Cache-Control': 'no-store',
                'Pragma': 'no-cache'
            });

            // Add auth token if available
            if (bridgeState.token) {
                headers.set('Authorization', `Bearer ${bridgeState.token}`);
            }

            // Merge custom headers
            if (options.headers) {
                Object.entries(options.headers).forEach(([key, value]) => {
                    headers.set(key, value);
                });
            }

            const fetchOptions = {
                method,
                headers,
                cache: 'no-store'
            };

            if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
                fetchOptions.body = JSON.stringify(data);
            }

            try {
                const response = await fetch(url, fetchOptions);
                
                // Parse response
                let responseData;
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    responseData = await response.json();
                } else {
                    responseData = await response.text();
                }

                if (!response.ok) {
                    const error = new Error(responseData?.detail || responseData?.message || `HTTP ${response.status}`);
                    error.status = response.status;
                    error.response = responseData;
                    throw error;
                }

                return responseData;

            } catch (e) {
                console.error(`[JupiterBridge] API error:`, e);
                throw e;
            }
        },

        /**
         * Upload a file
         */
        async upload(path, file, options = {}) {
            const url = `${bridgeState.apiBaseUrl}${path.startsWith('/') ? path : '/' + path}`;

            const formData = new FormData();
            formData.append('file', file);

            // Add extra fields if provided
            if (options.fields) {
                Object.entries(options.fields).forEach(([key, value]) => {
                    formData.append(key, value);
                });
            }

            const headers = new Headers();
            if (bridgeState.token) {
                headers.set('Authorization', `Bearer ${bridgeState.token}`);
            }

            const response = await fetch(url, {
                method: 'POST',
                headers,
                body: formData
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `Upload failed: ${response.status}`);
            }

            return response.json();
        },

        /**
         * Download a file
         */
        async download(path, filename) {
            const url = `${bridgeState.apiBaseUrl}${path.startsWith('/') ? path : '/' + path}`;

            const headers = new Headers();
            if (bridgeState.token) {
                headers.set('Authorization', `Bearer ${bridgeState.token}`);
            }

            const response = await fetch(url, { headers });

            if (!response.ok) {
                throw new Error(`Download failed: ${response.status}`);
            }

            const blob = await response.blob();
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = filename || 'download';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
        }
    };

    // =============================================================================
    // WEBSOCKET MODULE
    // =============================================================================

    const ws = {
        /**
         * Connect to a WebSocket endpoint
         */
        connect(path = '/ws') {
            if (bridgeState.ws && bridgeState.ws.readyState === WebSocket.OPEN) {
                return Promise.resolve(bridgeState.ws);
            }

            return new Promise((resolve, reject) => {
                try {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}${path}`;
                    
                    bridgeState.ws = new WebSocket(wsUrl);

                    bridgeState.ws.onopen = () => {
                        console.log('[JupiterBridge] WebSocket connected');
                        bridgeState.wsReconnectAttempts = 0;
                        resolve(bridgeState.ws);
                    };

                    bridgeState.ws.onmessage = (event) => {
                        try {
                            const data = JSON.parse(event.data);
                            this._handleMessage(data);
                        } catch (e) {
                            console.error('[JupiterBridge] WS message parse error:', e);
                        }
                    };

                    bridgeState.ws.onclose = () => {
                        console.log('[JupiterBridge] WebSocket closed');
                        this._scheduleReconnect(path);
                    };

                    bridgeState.ws.onerror = (error) => {
                        console.error('[JupiterBridge] WebSocket error:', error);
                        reject(error);
                    };

                } catch (e) {
                    reject(e);
                }
            });
        },

        /**
         * Disconnect WebSocket
         */
        disconnect() {
            if (bridgeState.ws) {
                bridgeState.ws.close();
                bridgeState.ws = null;
            }
        },

        /**
         * Send message via WebSocket
         */
        send(data) {
            if (bridgeState.ws && bridgeState.ws.readyState === WebSocket.OPEN) {
                bridgeState.ws.send(JSON.stringify(data));
                return true;
            }
            return false;
        },

        /**
         * Check if WebSocket is connected
         */
        isConnected() {
            return bridgeState.ws && bridgeState.ws.readyState === WebSocket.OPEN;
        },

        /**
         * Handle incoming WebSocket message
         * @private
         */
        _handleMessage(data) {
            // Bridge events from backend
            if (data.type === 'bridge_event' && data.topic) {
                events.emit(data.topic, data.payload);
            }
            // Direct event
            else if (data.event) {
                events.emit(data.event, data.data || data.payload);
            }
            // Generic message
            else {
                events.emit('ws:message', data);
            }
        },

        /**
         * Schedule WebSocket reconnection
         * @private
         */
        _scheduleReconnect(path) {
            if (bridgeState.wsReconnectAttempts >= bridgeState.wsMaxReconnectAttempts) {
                console.error('[JupiterBridge] Max reconnect attempts reached');
                events.emit('ws:disconnected', { permanent: true });
                return;
            }

            const delay = bridgeState.wsReconnectDelay * Math.pow(2, bridgeState.wsReconnectAttempts);
            bridgeState.wsReconnectAttempts++;

            console.log(`[JupiterBridge] Reconnecting in ${delay}ms (attempt ${bridgeState.wsReconnectAttempts})`);
            setTimeout(() => this.connect(path), delay);
        }
    };

    // =============================================================================
    // EVENTS MODULE
    // =============================================================================

    const events = {
        /**
         * Subscribe to an event topic
         */
        subscribe(topic, callback) {
            if (typeof callback !== 'function') {
                throw new Error('Callback must be a function');
            }

            if (!bridgeState.eventSubscriptions.has(topic)) {
                bridgeState.eventSubscriptions.set(topic, new Set());
            }

            bridgeState.eventSubscriptions.get(topic).add(callback);

            // Return unsubscribe function
            return () => this.unsubscribe(topic, callback);
        },

        /**
         * Unsubscribe from an event topic
         */
        unsubscribe(topic, callback) {
            const subscribers = bridgeState.eventSubscriptions.get(topic);
            if (subscribers) {
                subscribers.delete(callback);
            }
        },

        /**
         * Emit an event to all subscribers
         */
        emit(topic, payload) {
            const subscribers = bridgeState.eventSubscriptions.get(topic);
            if (subscribers) {
                subscribers.forEach(callback => {
                    try {
                        callback(payload);
                    } catch (e) {
                        console.error(`[JupiterBridge] Event handler error for ${topic}:`, e);
                    }
                });
            }

            // Also emit to wildcard subscribers
            const wildcardSubs = bridgeState.eventSubscriptions.get('*');
            if (wildcardSubs) {
                wildcardSubs.forEach(callback => {
                    try {
                        callback({ topic, payload });
                    } catch (e) {
                        console.error(`[JupiterBridge] Wildcard handler error:`, e);
                    }
                });
            }
        },

        /**
         * Subscribe to an event once
         */
        once(topic, callback) {
            const wrapper = (payload) => {
                this.unsubscribe(topic, wrapper);
                callback(payload);
            };
            return this.subscribe(topic, wrapper);
        },

        /**
         * Clear all subscriptions for a topic
         */
        clear(topic) {
            if (topic) {
                bridgeState.eventSubscriptions.delete(topic);
            } else {
                bridgeState.eventSubscriptions.clear();
            }
        }
    };

    // =============================================================================
    // I18N MODULE
    // =============================================================================

    const i18n = {
        /**
         * Translate a key
         */
        t(key, params = {}) {
            // Use global state translations if available
            const translations = global.state?.i18n?.translations || {};
            let value = translations[key] || key;

            // Replace parameters
            Object.entries(params).forEach(([k, v]) => {
                value = value.replace(new RegExp(`{${k}}`, 'g'), v);
            });

            return value;
        },

        /**
         * Get current language
         */
        getLanguage() {
            return global.state?.i18n?.lang || 'en';
        },

        /**
         * Set language
         */
        async setLanguage(lang) {
            if (typeof global.setLanguage === 'function') {
                await global.setLanguage(lang);
            }
        },

        /**
         * Get available languages
         */
        getAvailableLanguages() {
            return global.state?.i18n?.availableLanguages || ['en', 'fr'];
        }
    };

    // =============================================================================
    // NOTIFICATIONS MODULE
    // =============================================================================

    const notify = {
        /**
         * Show an info notification
         */
        info(message, options = {}) {
            return this._show('info', message, options);
        },

        /**
         * Show a success notification
         */
        success(message, options = {}) {
            return this._show('success', message, options);
        },

        /**
         * Show a warning notification
         */
        warning(message, options = {}) {
            return this._show('warning', message, options);
        },

        /**
         * Show an error notification
         */
        error(message, options = {}) {
            return this._show('error', message, options);
        },

        /**
         * Show a notification
         * @private
         */
        _show(type, message, options = {}) {
            // Try to use global addLog if available
            if (typeof global.addLog === 'function') {
                global.addLog(message, type.toUpperCase());
            }

            // Create toast notification
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <span class="toast-icon">${this._getIcon(type)}</span>
                <span class="toast-message">${escapeHtml(message)}</span>
                <button class="toast-close" onclick="this.parentElement.remove()">×</button>
            `;

            // Get or create toast container
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                container.className = 'toast-container';
                document.body.appendChild(container);
            }

            container.appendChild(toast);

            // Auto-dismiss
            const duration = options.duration || 5000;
            if (duration > 0) {
                setTimeout(() => {
                    if (toast.parentElement) {
                        toast.classList.add('toast-fade-out');
                        setTimeout(() => toast.remove(), 300);
                    }
                }, duration);
            }

            return toast;
        },

        /**
         * Get icon for notification type
         * @private
         */
        _getIcon(type) {
            const icons = {
                info: 'ℹ️',
                success: '✅',
                warning: '⚠️',
                error: '❌'
            };
            return icons[type] || 'ℹ️';
        }
    };

    // =============================================================================
    // MODAL MODULE
    // =============================================================================

    const modal = {
        /**
         * Show a modal dialog
         */
        show(options = {}) {
            const {
                title = '',
                content = '',
                buttons = [],
                closable = true,
                size = 'medium',  // small, medium, large
                onClose = null
            } = options;

            // Create modal
            const modalEl = document.createElement('div');
            modalEl.className = 'jupiter-modal-overlay';
            modalEl.innerHTML = `
                <div class="jupiter-modal jupiter-modal-${size}">
                    <div class="jupiter-modal-header">
                        <h3 class="jupiter-modal-title">${escapeHtml(title)}</h3>
                        ${closable ? '<button class="jupiter-modal-close">×</button>' : ''}
                    </div>
                    <div class="jupiter-modal-body">${content}</div>
                    <div class="jupiter-modal-footer"></div>
                </div>
            `;

            // Add buttons
            const footer = modalEl.querySelector('.jupiter-modal-footer');
            buttons.forEach(btn => {
                const button = document.createElement('button');
                button.className = `btn ${btn.class || 'btn-secondary'}`;
                button.textContent = btn.label;
                button.onclick = () => {
                    if (btn.action) btn.action();
                    if (btn.close !== false) this.close(modalEl);
                };
                footer.appendChild(button);
            });

            // Close handlers
            if (closable) {
                modalEl.querySelector('.jupiter-modal-close').onclick = () => {
                    this.close(modalEl);
                    if (onClose) onClose();
                };
                modalEl.onclick = (e) => {
                    if (e.target === modalEl) {
                        this.close(modalEl);
                        if (onClose) onClose();
                    }
                };
            }

            document.body.appendChild(modalEl);
            document.body.classList.add('modal-open');

            return modalEl;
        },

        /**
         * Show a confirmation dialog
         */
        confirm(message, options = {}) {
            return new Promise((resolve) => {
                this.show({
                    title: options.title || i18n.t('confirm'),
                    content: `<p>${escapeHtml(message)}</p>`,
                    buttons: [
                        {
                            label: options.cancelLabel || i18n.t('cancel'),
                            class: 'btn-secondary',
                            action: () => resolve(false)
                        },
                        {
                            label: options.confirmLabel || i18n.t('confirm'),
                            class: options.danger ? 'btn-danger' : 'btn-primary',
                            action: () => resolve(true)
                        }
                    ],
                    onClose: () => resolve(false)
                });
            });
        },

        /**
         * Show an alert dialog
         */
        alert(message, options = {}) {
            return new Promise((resolve) => {
                this.show({
                    title: options.title || i18n.t('alert'),
                    content: `<p>${escapeHtml(message)}</p>`,
                    buttons: [
                        {
                            label: options.okLabel || i18n.t('ok') || 'OK',
                            class: 'btn-primary',
                            action: () => resolve()
                        }
                    ],
                    onClose: () => resolve()
                });
            });
        },

        /**
         * Show a prompt dialog
         */
        prompt(message, options = {}) {
            return new Promise((resolve) => {
                const inputId = `prompt-${Date.now()}`;
                const modal = this.show({
                    title: options.title || i18n.t('prompt'),
                    content: `
                        <p>${escapeHtml(message)}</p>
                        <input type="${options.type || 'text'}" 
                               id="${inputId}" 
                               class="form-input" 
                               value="${escapeHtml(options.defaultValue || '')}"
                               placeholder="${escapeHtml(options.placeholder || '')}">
                    `,
                    buttons: [
                        {
                            label: options.cancelLabel || i18n.t('cancel'),
                            class: 'btn-secondary',
                            action: () => resolve(null)
                        },
                        {
                            label: options.okLabel || i18n.t('ok') || 'OK',
                            class: 'btn-primary',
                            action: () => {
                                const input = modal.querySelector(`#${inputId}`);
                                resolve(input?.value || '');
                            }
                        }
                    ],
                    onClose: () => resolve(null)
                });

                // Focus input
                setTimeout(() => {
                    const input = modal.querySelector(`#${inputId}`);
                    if (input) input.focus();
                }, 100);
            });
        },

        /**
         * Close a modal
         */
        close(modalEl) {
            if (modalEl && modalEl.parentElement) {
                modalEl.remove();
            }
            // Check if any modals remain
            if (!document.querySelector('.jupiter-modal-overlay')) {
                document.body.classList.remove('modal-open');
            }
        },

        /**
         * Close all modals
         */
        closeAll() {
            document.querySelectorAll('.jupiter-modal-overlay').forEach(m => m.remove());
            document.body.classList.remove('modal-open');
        }
    };

    // =============================================================================
    // CONFIG MODULE
    // =============================================================================

    const config = {
        /**
         * Get plugin configuration
         */
        async get(pluginId) {
            return api.get(`/plugins/${pluginId}/config`);
        },

        /**
         * Set plugin configuration
         */
        async set(pluginId, data) {
            return api.put(`/plugins/${pluginId}/config`, data);
        },

        /**
         * Reset plugin configuration to defaults
         */
        async reset(pluginId) {
            return api.post(`/plugins/${pluginId}/reset-settings`);
        },

        /**
         * Get configuration schema
         */
        async getSchema(pluginId) {
            const response = await api.get(`/plugins/${pluginId}/config`);
            return response.config_schema || null;
        }
    };

    // =============================================================================
    // PLUGINS MODULE
    // =============================================================================

    const plugins = {
        /**
         * Get plugin version
         */
        async getVersion(pluginId) {
            const info = await api.get(`/plugins/v2/${pluginId}`);
            return info?.version || 'unknown';
        },

        /**
         * Check for plugin updates
         */
        async checkUpdate(pluginId) {
            try {
                const response = await api.get(`/plugins/${pluginId}/check-update`);
                return response;
            } catch (e) {
                return { hasUpdate: false, error: e.message };
            }
        },

        /**
         * Update a plugin
         */
        async update(pluginId, version = null) {
            const confirmed = await modal.confirm(
                i18n.t('plugin_update_confirm', { plugin: pluginId }),
                { danger: false }
            );
            if (!confirmed) return { cancelled: true };

            return api.post(`/plugins/${pluginId}/update`, { version });
        },

        /**
         * Get plugin list
         */
        async list(filters = {}) {
            return api.get('/plugins/v2', { params: filters });
        },

        /**
         * Get plugin details
         */
        async get(pluginId) {
            return api.get(`/plugins/v2/${pluginId}`);
        },

        /**
         * Get plugin health
         */
        async health(pluginId) {
            return api.get(`/plugins/${pluginId}/health`);
        },

        /**
         * Get plugin metrics
         */
        async metrics(pluginId) {
            return api.get(`/plugins/${pluginId}/metrics`);
        },

        /**
         * Enable a plugin
         */
        async enable(pluginId) {
            return api.post(`/plugins/${pluginId}/enable`);
        },

        /**
         * Disable a plugin
         */
        async disable(pluginId) {
            return api.post(`/plugins/${pluginId}/disable`);
        },

        /**
         * Reload a plugin (dev mode)
         */
        async reload(pluginId) {
            return api.post(`/plugins/${pluginId}/reload`);
        }
    };

    // =============================================================================
    // AI MODULE
    // =============================================================================

    const ai = {
        /**
         * Send context to AI agent
         */
        async sendContext(pluginId, data) {
            return api.post(`/plugins/${pluginId}/ai/context`, data);
        },

        /**
         * Export plugin data for AI consumption
         */
        async exportForAI(pluginId, options = {}) {
            const response = await api.get(`/plugins/${pluginId}/export`, {
                params: { format: 'ai', ...options }
            });
            return response;
        }
    };

    // =============================================================================
    // UTILITIES
    // =============================================================================

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(str);
        return div.innerHTML;
    }

    /**
     * Initialize the Jupiter Bridge
     */
    function init(options = {}) {
        if (bridgeState.initialized) {
            console.warn('[JupiterBridge] Already initialized');
            return;
        }

        // Set API base URL
        bridgeState.apiBaseUrl = options.apiBaseUrl 
            || global.state?.apiBaseUrl 
            || `${window.location.protocol}//${window.location.host}`;

        // Set token if available
        bridgeState.token = options.token 
            || global.state?.token 
            || localStorage.getItem('jupiter-token');

        // Auto-connect WebSocket if requested
        if (options.connectWs !== false) {
            ws.connect(options.wsPath || '/ws').catch(e => {
                console.warn('[JupiterBridge] Initial WS connection failed:', e);
            });
        }

        bridgeState.initialized = true;
        console.log(`[JupiterBridge] Initialized v${VERSION}`);
    }

    /**
     * Get bridge version
     */
    function getVersion() {
        return VERSION;
    }

    /**
     * Check if bridge is initialized
     */
    function isInitialized() {
        return bridgeState.initialized;
    }

    /**
     * Update token
     */
    function setToken(token) {
        bridgeState.token = token;
    }

    // =============================================================================
    // PUBLIC API
    // =============================================================================

    const jupiterBridge = {
        // Core
        init,
        getVersion,
        isInitialized,
        setToken,

        // Modules
        api,
        ws,
        events,
        i18n,
        notify,
        modal,
        config,
        plugins,
        ai,

        // Utilities
        escapeHtml,

        // Internal state (for debugging)
        _state: bridgeState
    };

    // Export globally
    global.jupiterBridge = jupiterBridge;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = jupiterBridge;
    }

})(typeof window !== 'undefined' ? window : this);
