/**
 * Jupiter Plugin Container Module
 * 
 * Version: 0.1.0
 * 
 * Provides dynamic plugin panel mounting, lazy loading, and routing
 * for the Jupiter WebUI plugin system v2.
 * 
 * Features:
 * - Dynamic container creation for plugin panels
 * - Lazy loading of plugin bundles (JS/CSS)
 * - Route management for /plugins/<id> URLs
 * - Plugin lifecycle management (mount/unmount)
 * - Error boundary for plugin failures
 */

(function(global) {
    'use strict';

    const VERSION = '0.1.0';

    // =============================================================================
    // PLUGIN CONTAINER STATE
    // =============================================================================

    const containerState = {
        initialized: false,
        plugins: new Map(),           // plugin_id -> PluginInstance
        loadedBundles: new Set(),     // Loaded JS bundle URLs
        loadedStyles: new Set(),      // Loaded CSS URLs
        currentPlugin: null,          // Currently active plugin ID
        containerElement: null,       // Main container DOM element
        errorHandlers: [],            // Error callback handlers
        mountCallbacks: [],           // Mount event callbacks
        unmountCallbacks: []          // Unmount event callbacks
    };

    // =============================================================================
    // PLUGIN INSTANCE CLASS
    // =============================================================================

    /**
     * Represents a mounted plugin instance
     */
    class PluginInstance {
        constructor(pluginId, manifest) {
            this.id = pluginId;
            this.manifest = manifest;
            this.element = null;
            this.mounted = false;
            this.module = null;        // Loaded plugin module
            this.error = null;
            this.mountedAt = null;
            this.unmountedAt = null;
        }

        /**
         * Create the DOM container for this plugin
         */
        createContainer() {
            if (this.element) return this.element;

            const container = document.createElement('div');
            container.id = `plugin-panel-${this.id}`;
            container.className = 'plugin-panel hidden';
            container.dataset.pluginId = this.id;
            container.setAttribute('role', 'tabpanel');
            container.setAttribute('aria-label', this.manifest?.name || this.id);

            // Add loading placeholder
            container.innerHTML = `
                <div class="plugin-loading">
                    <div class="plugin-loading-spinner"></div>
                    <p data-i18n="loading_plugin">Loading plugin...</p>
                </div>
            `;

            this.element = container;
            return container;
        }

        /**
         * Mount the plugin's content
         */
        async mount(content) {
            if (!this.element) {
                throw new Error(`Plugin ${this.id} has no container element`);
            }

            try {
                // Clear loading state
                this.element.innerHTML = '';

                // If content is HTML string, inject it
                if (typeof content === 'string') {
                    this.element.innerHTML = content;
                }
                // If content is DOM element, append it
                else if (content instanceof HTMLElement) {
                    this.element.appendChild(content);
                }
                // If content is a component with render method
                else if (content && typeof content.render === 'function') {
                    const rendered = await content.render();
                    if (typeof rendered === 'string') {
                        this.element.innerHTML = rendered;
                    } else if (rendered instanceof HTMLElement) {
                        this.element.appendChild(rendered);
                    }
                }

                // Call plugin's mount lifecycle if available
                if (this.module && typeof this.module.onMount === 'function') {
                    await this.module.onMount(this.element);
                }

                this.mounted = true;
                this.mountedAt = new Date();
                this.error = null;

            } catch (e) {
                this.error = e;
                this.element.innerHTML = `
                    <div class="plugin-error">
                        <h3>⚠️ Plugin Error</h3>
                        <p>${escapeHtml(e.message)}</p>
                        <button class="btn btn-secondary" onclick="jupiterPluginContainer.reloadPlugin('${this.id}')">
                            Retry
                        </button>
                    </div>
                `;
                throw e;
            }
        }

        /**
         * Unmount the plugin
         */
        async unmount() {
            if (!this.mounted) return;

            try {
                // Call plugin's unmount lifecycle if available
                if (this.module && typeof this.module.onUnmount === 'function') {
                    await this.module.onUnmount();
                }

                this.mounted = false;
                this.unmountedAt = new Date();

            } catch (e) {
                console.error(`[PluginContainer] Error unmounting ${this.id}:`, e);
            }
        }

        /**
         * Show the plugin panel
         */
        show() {
            if (this.element) {
                this.element.classList.remove('hidden');
                this.element.setAttribute('aria-hidden', 'false');
            }
        }

        /**
         * Hide the plugin panel
         */
        hide() {
            if (this.element) {
                this.element.classList.add('hidden');
                this.element.setAttribute('aria-hidden', 'true');
            }
        }

        /**
         * Get plugin info
         */
        getInfo() {
            return {
                id: this.id,
                name: this.manifest?.name || this.id,
                version: this.manifest?.version || 'unknown',
                mounted: this.mounted,
                error: this.error?.message || null,
                mountedAt: this.mountedAt?.toISOString() || null
            };
        }
    }

    // =============================================================================
    // BUNDLE LOADER
    // =============================================================================

    /**
     * Load a JavaScript bundle dynamically
     */
    async function loadJSBundle(url, pluginId) {
        if (containerState.loadedBundles.has(url)) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = url;
            script.async = true;
            script.dataset.pluginId = pluginId;

            script.onload = () => {
                containerState.loadedBundles.add(url);
                resolve();
            };

            script.onerror = () => {
                reject(new Error(`Failed to load bundle: ${url}`));
            };

            document.head.appendChild(script);
        });
    }

    /**
     * Load a CSS stylesheet dynamically
     */
    async function loadCSSBundle(url, pluginId) {
        if (containerState.loadedStyles.has(url)) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = url;
            link.dataset.pluginId = pluginId;

            link.onload = () => {
                containerState.loadedStyles.add(url);
                resolve();
            };

            link.onerror = () => {
                reject(new Error(`Failed to load stylesheet: ${url}`));
            };

            document.head.appendChild(link);
        });
    }

    /**
     * Unload bundles for a specific plugin
     */
    function unloadPluginBundles(pluginId) {
        // Remove JS
        document.querySelectorAll(`script[data-plugin-id="${pluginId}"]`).forEach(el => {
            const url = el.src;
            containerState.loadedBundles.delete(url);
            el.remove();
        });

        // Remove CSS
        document.querySelectorAll(`link[data-plugin-id="${pluginId}"]`).forEach(el => {
            const url = el.href;
            containerState.loadedStyles.delete(url);
            el.remove();
        });
    }

    // =============================================================================
    // ROUTING
    // =============================================================================

    /**
     * Parse plugin route from URL hash
     */
    function parsePluginRoute() {
        const hash = window.location.hash;
        const match = hash.match(/^#\/plugins\/([a-z][a-z0-9_]*)(?:\/(.*))?$/);
        if (match) {
            return {
                pluginId: match[1],
                subRoute: match[2] || ''
            };
        }
        return null;
    }

    /**
     * Navigate to a plugin route
     */
    function navigateToPlugin(pluginId, subRoute = '') {
        const hash = subRoute 
            ? `#/plugins/${pluginId}/${subRoute}`
            : `#/plugins/${pluginId}`;
        window.location.hash = hash;
    }

    /**
     * Handle route changes
     */
    function handleRouteChange() {
        const route = parsePluginRoute();
        if (route) {
            showPlugin(route.pluginId, route.subRoute);
        } else {
            hideAllPlugins();
        }
    }

    // =============================================================================
    // PLUGIN MANAGEMENT
    // =============================================================================

    /**
     * Initialize the plugin container system
     */
    function init(containerId = 'plugin-views-container') {
        if (containerState.initialized) {
            console.warn('[PluginContainer] Already initialized');
            return;
        }

        // Find or create container element
        let container = document.getElementById(containerId);
        if (!container) {
            container = document.createElement('div');
            container.id = containerId;
            container.className = 'plugin-views-container';
            document.body.appendChild(container);
        }
        containerState.containerElement = container;

        // Setup route handling
        window.addEventListener('hashchange', handleRouteChange);

        // Handle initial route
        handleRouteChange();

        containerState.initialized = true;
        console.log(`[PluginContainer] Initialized v${VERSION}`);
    }

    /**
     * Register a plugin with the container
     */
    function registerPlugin(pluginId, manifest) {
        if (containerState.plugins.has(pluginId)) {
            console.warn(`[PluginContainer] Plugin ${pluginId} already registered`);
            return containerState.plugins.get(pluginId);
        }

        const instance = new PluginInstance(pluginId, manifest);
        const panelElement = instance.createContainer();

        // Add to container
        if (containerState.containerElement) {
            containerState.containerElement.appendChild(panelElement);
        }

        containerState.plugins.set(pluginId, instance);
        console.log(`[PluginContainer] Registered plugin: ${pluginId}`);

        return instance;
    }

    /**
     * Unregister a plugin from the container
     */
    async function unregisterPlugin(pluginId) {
        const instance = containerState.plugins.get(pluginId);
        if (!instance) return;

        // Unmount if mounted
        await instance.unmount();

        // Remove DOM element
        if (instance.element && instance.element.parentNode) {
            instance.element.parentNode.removeChild(instance.element);
        }

        // Unload bundles
        unloadPluginBundles(pluginId);

        containerState.plugins.delete(pluginId);
        console.log(`[PluginContainer] Unregistered plugin: ${pluginId}`);
    }

    /**
     * Load and mount a plugin
     */
    async function loadPlugin(pluginId, options = {}) {
        let instance = containerState.plugins.get(pluginId);

        // Register if not exists
        if (!instance) {
            instance = registerPlugin(pluginId, options.manifest || {});
        }

        try {
            // Load bundles if specified
            if (options.jsUrl) {
                await loadJSBundle(options.jsUrl, pluginId);
            }
            if (options.cssUrl) {
                await loadCSSBundle(options.cssUrl, pluginId);
            }

            // Get plugin module if registered globally
            const moduleKey = `jupiterPlugin_${pluginId}`;
            if (global[moduleKey]) {
                instance.module = global[moduleKey];
            }

            // Load content
            let content = options.content;
            if (!content && options.contentUrl) {
                const response = await fetch(options.contentUrl);
                if (response.ok) {
                    content = await response.text();
                }
            }

            // Mount
            if (content) {
                await instance.mount(content);
            }

            // Fire mount callbacks
            containerState.mountCallbacks.forEach(cb => {
                try { cb(pluginId, instance); } catch (e) { console.error(e); }
            });

            return instance;

        } catch (e) {
            console.error(`[PluginContainer] Failed to load plugin ${pluginId}:`, e);

            // Fire error handlers
            containerState.errorHandlers.forEach(cb => {
                try { cb(pluginId, e); } catch (err) { console.error(err); }
            });

            throw e;
        }
    }

    /**
     * Reload a plugin
     */
    async function reloadPlugin(pluginId) {
        const instance = containerState.plugins.get(pluginId);
        if (!instance) return;

        const manifest = instance.manifest;

        await unregisterPlugin(pluginId);
        await loadPlugin(pluginId, { manifest });
    }

    /**
     * Show a plugin panel
     */
    async function showPlugin(pluginId, subRoute = '') {
        // Hide current plugin
        if (containerState.currentPlugin && containerState.currentPlugin !== pluginId) {
            hidePlugin(containerState.currentPlugin);
        }

        let instance = containerState.plugins.get(pluginId);

        // Lazy load if not registered
        if (!instance) {
            try {
                // Fetch plugin UI manifest from API
                const apiBaseUrl = global.state?.apiBaseUrl || '';
                const response = await fetch(`${apiBaseUrl}/plugins/${pluginId}/ui`);
                if (response.ok) {
                    const data = await response.json();
                    instance = await loadPlugin(pluginId, {
                        manifest: data.manifest || {},
                        content: data.html,
                        jsUrl: data.js_url,
                        cssUrl: data.css_url
                    });
                } else {
                    throw new Error(`Failed to fetch plugin UI: ${response.status}`);
                }
            } catch (e) {
                console.error(`[PluginContainer] Could not show plugin ${pluginId}:`, e);
                return;
            }
        }

        if (instance) {
            instance.show();
            containerState.currentPlugin = pluginId;

            // Notify plugin of sub-route change
            if (instance.module && typeof instance.module.onRouteChange === 'function') {
                instance.module.onRouteChange(subRoute);
            }
        }
    }

    /**
     * Hide a plugin panel
     */
    function hidePlugin(pluginId) {
        const instance = containerState.plugins.get(pluginId);
        if (instance) {
            instance.hide();
        }

        if (containerState.currentPlugin === pluginId) {
            containerState.currentPlugin = null;
        }
    }

    /**
     * Hide all plugin panels
     */
    function hideAllPlugins() {
        containerState.plugins.forEach((instance, pluginId) => {
            instance.hide();
        });
        containerState.currentPlugin = null;
    }

    /**
     * Get a plugin instance
     */
    function getPlugin(pluginId) {
        return containerState.plugins.get(pluginId);
    }

    /**
     * Get all registered plugins
     */
    function getAllPlugins() {
        return Array.from(containerState.plugins.values()).map(p => p.getInfo());
    }

    /**
     * Check if a plugin is loaded
     */
    function isPluginLoaded(pluginId) {
        const instance = containerState.plugins.get(pluginId);
        return instance && instance.mounted;
    }

    // =============================================================================
    // EVENT HANDLERS
    // =============================================================================

    /**
     * Register an error handler
     */
    function onError(callback) {
        if (typeof callback === 'function') {
            containerState.errorHandlers.push(callback);
        }
    }

    /**
     * Register a mount callback
     */
    function onMount(callback) {
        if (typeof callback === 'function') {
            containerState.mountCallbacks.push(callback);
        }
    }

    /**
     * Register an unmount callback
     */
    function onUnmount(callback) {
        if (typeof callback === 'function') {
            containerState.unmountCallbacks.push(callback);
        }
    }

    // =============================================================================
    // UTILITIES
    // =============================================================================

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Get container version
     */
    function getVersion() {
        return VERSION;
    }

    // =============================================================================
    // PUBLIC API
    // =============================================================================

    const pluginContainer = {
        // Core
        init,
        getVersion,

        // Plugin management
        registerPlugin,
        unregisterPlugin,
        loadPlugin,
        reloadPlugin,

        // Navigation
        showPlugin,
        hidePlugin,
        hideAllPlugins,
        navigateToPlugin,

        // Query
        getPlugin,
        getAllPlugins,
        isPluginLoaded,

        // Bundle loading
        loadJSBundle,
        loadCSSBundle,

        // Events
        onError,
        onMount,
        onUnmount,

        // Internal state (for debugging)
        _state: containerState
    };

    // Export globally
    global.jupiterPluginContainer = pluginContainer;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = pluginContainer;
    }

})(typeof window !== 'undefined' ? window : this);
