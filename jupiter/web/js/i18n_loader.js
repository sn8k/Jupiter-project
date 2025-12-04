/**
 * i18n Loader - Jupiter Bridge Frontend
 * 
 * Provides internationalization support for the Jupiter UI.
 * Features:
 * - Dynamic language loading
 * - Fallback language support
 * - DOM automatic translation
 * - Interpolation support
 * - Plural forms handling
 * - Language detection
 * 
 * @version 0.2.0
 * @module jupiter/web/js/i18n_loader
 */

(function(window) {
    'use strict';

    /**
     * i18n Loader for Jupiter
     */
    class I18nLoader {
        /**
         * @param {Object} options - Configuration options
         * @param {string} [options.defaultLang='en'] - Default language
         * @param {string} [options.fallbackLang='en'] - Fallback language
         * @param {string} [options.langPath='lang'] - Path to language files
         * @param {string} [options.attribute='data-i18n'] - Translation attribute
         */
        constructor(options = {}) {
            this.defaultLang = options.defaultLang || 'en';
            this.fallbackLang = options.fallbackLang || 'en';
            this.langPath = options.langPath || 'lang';
            this.attribute = options.attribute || 'data-i18n';
            
            // State
            this.currentLang = null;
            this.translations = {};
            this.loadedLanguages = new Set();
            
            // Cache
            this.cache = new Map();
            
            // Event callbacks
            this.onLanguageChange = options.onLanguageChange || null;
        }

        /**
         * Initialize i18n loader
         * @param {string} [lang] - Initial language (auto-detected if not provided)
         * @returns {Promise<void>}
         */
        async init(lang = null) {
            const detectedLang = lang || this._detectLanguage();
            await this.setLanguage(detectedLang);
            
            // Translate initial DOM
            this.translateDOM();
            
            // Watch for new elements
            this._setupMutationObserver();
            
            console.log(`[I18nLoader] Initialized with language: ${this.currentLang}`);
        }

        /**
         * Detect user's preferred language
         * @private
         * @returns {string} Detected language code
         */
        _detectLanguage() {
            // 1. Check localStorage
            const stored = localStorage.getItem('jupiter_language');
            if (stored && this._isValidLang(stored)) {
                return stored;
            }
            
            // 2. Check URL parameter
            const urlParams = new URLSearchParams(window.location.search);
            const urlLang = urlParams.get('lang');
            if (urlLang && this._isValidLang(urlLang)) {
                return urlLang;
            }
            
            // 3. Check browser language
            const browserLang = navigator.language?.split('-')[0];
            if (browserLang && this._isValidLang(browserLang)) {
                return browserLang;
            }
            
            // 4. Fallback to default
            return this.defaultLang;
        }

        /**
         * Check if a language code is valid
         * @private
         * @param {string} lang - Language code
         * @returns {boolean}
         */
        _isValidLang(lang) {
            // Basic validation - could be extended to check available languages
            return /^[a-z]{2}(-[A-Z]{2})?$/.test(lang);
        }

        /**
         * Set current language
         * @param {string} lang - Language code
         * @returns {Promise<void>}
         */
        async setLanguage(lang) {
            if (this.currentLang === lang && this.loadedLanguages.has(lang)) {
                return;
            }
            
            try {
                // Load language if not already loaded
                if (!this.loadedLanguages.has(lang)) {
                    await this._loadLanguage(lang);
                }
                
                // Load fallback if different
                if (lang !== this.fallbackLang && !this.loadedLanguages.has(this.fallbackLang)) {
                    await this._loadLanguage(this.fallbackLang);
                }
                
                this.currentLang = lang;
                
                // Persist preference
                localStorage.setItem('jupiter_language', lang);
                
                // Update document lang attribute
                document.documentElement.lang = lang;
                
                // Clear cache
                this.cache.clear();
                
                // Translate DOM
                this.translateDOM();
                
                // Callback
                if (this.onLanguageChange) {
                    this.onLanguageChange(lang);
                }
                
                // Emit event
                window.dispatchEvent(new CustomEvent('jupiter:languageChange', {
                    detail: { language: lang }
                }));
                
                console.log(`[I18nLoader] Language changed to: ${lang}`);
                
            } catch (error) {
                console.error(`[I18nLoader] Failed to set language ${lang}:`, error);
                
                // Try fallback
                if (lang !== this.fallbackLang) {
                    console.log(`[I18nLoader] Falling back to ${this.fallbackLang}`);
                    await this.setLanguage(this.fallbackLang);
                }
            }
        }

        /**
         * Load a language file
         * @private
         * @param {string} lang - Language code
         * @returns {Promise<Object>}
         */
        async _loadLanguage(lang) {
            try {
                const response = await fetch(`${this.langPath}/${lang}.json`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const data = await response.json();
                this.translations[lang] = data;
                this.loadedLanguages.add(lang);
                
                console.log(`[I18nLoader] Loaded language: ${lang}`);
                return data;
                
            } catch (error) {
                console.error(`[I18nLoader] Failed to load language ${lang}:`, error);
                throw error;
            }
        }

        /**
         * Load and merge plugin translations
         * @param {string} pluginId - Plugin identifier
         * @param {string} [lang] - Language code (defaults to current language)
         * @returns {Promise<boolean>} Success status
         */
        async loadPluginTranslations(pluginId, lang = null) {
            const targetLang = lang || this.currentLang;
            
            try {
                // Try to load plugin lang file from API
                const response = await fetch(`/api/v1/plugins/${pluginId}/lang/${targetLang}`);
                
                if (!response.ok) {
                    if (response.status === 404) {
                        // Plugin has no translations for this language
                        console.debug(`[I18nLoader] No ${targetLang} translations for plugin ${pluginId}`);
                        return false;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const pluginTranslations = await response.json();
                
                // Merge into existing translations with plugin namespace
                this._mergePluginTranslations(pluginId, targetLang, pluginTranslations);
                
                console.log(`[I18nLoader] Loaded translations for plugin ${pluginId} (${targetLang})`);
                return true;
                
            } catch (error) {
                console.warn(`[I18nLoader] Failed to load translations for plugin ${pluginId}:`, error);
                return false;
            }
        }

        /**
         * Merge plugin translations into main translations
         * @private
         * @param {string} pluginId - Plugin identifier
         * @param {string} lang - Language code
         * @param {Object} translations - Plugin translations
         */
        _mergePluginTranslations(pluginId, lang, translations) {
            if (!this.translations[lang]) {
                this.translations[lang] = {};
            }
            
            // Create plugin namespace
            if (!this.translations[lang].plugin) {
                this.translations[lang].plugin = {};
            }
            
            // Merge translations under plugin namespace
            this.translations[lang].plugin[pluginId] = {
                ...this.translations[lang].plugin[pluginId],
                ...translations
            };
            
            // Clear cache for this plugin's keys
            for (const key of this.cache.keys()) {
                if (key.startsWith(`plugin.${pluginId}`)) {
                    this.cache.delete(key);
                }
            }
        }

        /**
         * Load all plugin translations from manifest
         * @returns {Promise<number>} Number of plugins with loaded translations
         */
        async loadAllPluginTranslations() {
            try {
                // Get list of plugins with UI contributions
                const response = await fetch('/api/v1/plugins/ui-manifest');
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                
                const manifest = await response.json();
                const plugins = manifest.plugins || Object.keys(manifest);
                
                let loadedCount = 0;
                
                // Load translations for each plugin
                const loadPromises = plugins.map(async (pluginId) => {
                    const loaded = await this.loadPluginTranslations(pluginId);
                    if (loaded) loadedCount++;
                });
                
                await Promise.all(loadPromises);
                
                console.log(`[I18nLoader] Loaded translations for ${loadedCount}/${plugins.length} plugins`);
                return loadedCount;
                
            } catch (error) {
                console.error('[I18nLoader] Failed to load plugin translations:', error);
                return 0;
            }
        }

        /**
         * Get translation for a plugin key
         * Shorthand for t('plugin.pluginId.key')
         * @param {string} pluginId - Plugin identifier
         * @param {string} key - Translation key within plugin namespace
         * @param {Object} [params] - Interpolation parameters
         * @returns {string} Translated string
         */
        pt(pluginId, key, params = {}) {
            return this.t(`plugin.${pluginId}.${key}`, params);
        }

        /**
         * Check if a plugin has translations loaded
         * @param {string} pluginId - Plugin identifier
         * @returns {boolean}
         */
        hasPluginTranslations(pluginId) {
            const translations = this.translations[this.currentLang];
            return !!(translations?.plugin?.[pluginId]);
        }

        /**
         * Get translation for a key
         * @param {string} key - Translation key (supports dot notation)
         * @param {Object} [params] - Interpolation parameters
         * @param {number} [count] - Count for pluralization
         * @returns {string} Translated string
         */
        t(key, params = {}, count = null) {
            // Check cache
            const cacheKey = `${key}:${JSON.stringify(params)}:${count}`;
            if (this.cache.has(cacheKey)) {
                return this.cache.get(cacheKey);
            }
            
            // Get translation
            let translation = this._getTranslation(key, this.currentLang);
            
            // Try fallback
            if (translation === null && this.currentLang !== this.fallbackLang) {
                translation = this._getTranslation(key, this.fallbackLang);
            }
            
            // Return key if not found
            if (translation === null) {
                console.warn(`[I18nLoader] Missing translation: ${key}`);
                return key;
            }
            
            // Handle pluralization
            if (count !== null && typeof translation === 'object') {
                translation = this._pluralize(translation, count);
            }
            
            // Handle object with 'one' key as default (for singular/plural)
            if (typeof translation === 'object' && translation.one) {
                translation = translation.one;
            }
            
            // Interpolate
            if (typeof translation === 'string' && Object.keys(params).length > 0) {
                translation = this._interpolate(translation, params);
            }
            
            // Cache result
            this.cache.set(cacheKey, translation);
            
            return translation;
        }

        /**
         * Get raw translation value
         * @private
         * @param {string} key - Translation key
         * @param {string} lang - Language code
         * @returns {string|Object|null}
         */
        _getTranslation(key, lang) {
            const translations = this.translations[lang];
            if (!translations) return null;
            
            // Support dot notation
            const parts = key.split('.');
            let value = translations;
            
            for (const part of parts) {
                if (value === null || typeof value !== 'object') {
                    return null;
                }
                value = value[part];
            }
            
            return value !== undefined ? value : null;
        }

        /**
         * Handle pluralization
         * @private
         * @param {Object} forms - Plural forms object
         * @param {number} count - Count value
         * @returns {string}
         */
        _pluralize(forms, count) {
            // Simple plural rules (can be extended for complex languages)
            if (count === 0 && forms.zero) return forms.zero;
            if (count === 1 && forms.one) return forms.one;
            if (count === 2 && forms.two) return forms.two;
            if (forms.few && count >= 2 && count <= 4) return forms.few;
            if (forms.many) return forms.many;
            if (forms.other) return forms.other;
            
            // Fallback
            return count === 1 ? (forms.one || forms.other || '') : (forms.other || forms.many || '');
        }

        /**
         * Interpolate parameters into string
         * @private
         * @param {string} str - String with placeholders
         * @param {Object} params - Parameters to interpolate
         * @returns {string}
         */
        _interpolate(str, params) {
            return str.replace(/\{\{(\w+)\}\}/g, (match, key) => {
                return params.hasOwnProperty(key) ? params[key] : match;
            });
        }

        /**
         * Translate all elements in DOM with translation attribute
         * @param {HTMLElement} [root=document.body] - Root element to translate
         */
        translateDOM(root = document.body) {
            if (!root) return;
            
            const elements = root.querySelectorAll(`[${this.attribute}]`);
            
            elements.forEach(el => {
                this._translateElement(el);
            });
        }

        /**
         * Translate a single element
         * @private
         * @param {HTMLElement} el - Element to translate
         */
        _translateElement(el) {
            const key = el.getAttribute(this.attribute);
            if (!key) return;
            
            // Get parameters from data attributes
            const params = {};
            for (const attr of el.attributes) {
                if (attr.name.startsWith('data-i18n-')) {
                    const paramKey = attr.name.replace('data-i18n-', '');
                    params[paramKey] = attr.value;
                }
            }
            
            // Get count for pluralization
            const count = el.hasAttribute('data-i18n-count') 
                ? parseInt(el.getAttribute('data-i18n-count'), 10) 
                : null;
            
            // Translate
            const translated = this.t(key, params, count);
            
            // Apply translation
            const target = el.getAttribute('data-i18n-target');
            
            switch (target) {
                case 'placeholder':
                    el.placeholder = translated;
                    break;
                case 'title':
                    el.title = translated;
                    break;
                case 'value':
                    el.value = translated;
                    break;
                case 'aria-label':
                    el.setAttribute('aria-label', translated);
                    break;
                case 'html':
                    el.innerHTML = translated;
                    break;
                default:
                    el.textContent = translated;
            }
        }

        /**
         * Setup mutation observer for dynamic content
         * @private
         */
        _setupMutationObserver() {
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                this.translateDOM(node);
                            }
                        });
                    }
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        }

        /**
         * Get current language
         * @returns {string}
         */
        getLanguage() {
            return this.currentLang;
        }

        /**
         * Get all loaded languages
         * @returns {string[]}
         */
        getLoadedLanguages() {
            return Array.from(this.loadedLanguages);
        }

        /**
         * Check if a key exists
         * @param {string} key - Translation key
         * @returns {boolean}
         */
        hasTranslation(key) {
            return this._getTranslation(key, this.currentLang) !== null ||
                   this._getTranslation(key, this.fallbackLang) !== null;
        }

        /**
         * Add translations dynamically (e.g., from plugins)
         * @param {string} lang - Language code
         * @param {Object} translations - Translations to add
         * @param {string} [namespace] - Optional namespace prefix
         */
        addTranslations(lang, translations, namespace = null) {
            if (!this.translations[lang]) {
                this.translations[lang] = {};
            }
            
            if (namespace) {
                // Add under namespace
                if (!this.translations[lang][namespace]) {
                    this.translations[lang][namespace] = {};
                }
                Object.assign(this.translations[lang][namespace], translations);
            } else {
                // Merge at root
                Object.assign(this.translations[lang], translations);
            }
            
            // Clear cache
            this.cache.clear();
            
            console.log(`[I18nLoader] Added translations for ${lang}${namespace ? ` (namespace: ${namespace})` : ''}`);
        }

        /**
         * Format a number according to locale
         * @param {number} value - Number to format
         * @param {Object} [options] - Intl.NumberFormat options
         * @returns {string}
         */
        formatNumber(value, options = {}) {
            return new Intl.NumberFormat(this.currentLang, options).format(value);
        }

        /**
         * Format a date according to locale
         * @param {Date|number|string} value - Date to format
         * @param {Object} [options] - Intl.DateTimeFormat options
         * @returns {string}
         */
        formatDate(value, options = {}) {
            const date = value instanceof Date ? value : new Date(value);
            return new Intl.DateTimeFormat(this.currentLang, options).format(date);
        }

        /**
         * Format relative time (e.g., "2 hours ago")
         * @param {Date|number} value - Date or timestamp
         * @param {string} [unit='auto'] - Time unit
         * @returns {string}
         */
        formatRelativeTime(value, unit = 'auto') {
            const date = value instanceof Date ? value : new Date(value);
            const now = Date.now();
            const diff = now - date.getTime();
            
            // Auto-detect unit
            let rtfUnit;
            let rtfValue;
            
            const seconds = Math.floor(diff / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);
            const months = Math.floor(days / 30);
            const years = Math.floor(days / 365);
            
            if (unit === 'auto') {
                if (years > 0) {
                    rtfUnit = 'year';
                    rtfValue = -years;
                } else if (months > 0) {
                    rtfUnit = 'month';
                    rtfValue = -months;
                } else if (days > 0) {
                    rtfUnit = 'day';
                    rtfValue = -days;
                } else if (hours > 0) {
                    rtfUnit = 'hour';
                    rtfValue = -hours;
                } else if (minutes > 0) {
                    rtfUnit = 'minute';
                    rtfValue = -minutes;
                } else {
                    rtfUnit = 'second';
                    rtfValue = -seconds;
                }
            } else {
                rtfUnit = unit;
                switch (unit) {
                    case 'second': rtfValue = -seconds; break;
                    case 'minute': rtfValue = -minutes; break;
                    case 'hour': rtfValue = -hours; break;
                    case 'day': rtfValue = -days; break;
                    case 'month': rtfValue = -months; break;
                    case 'year': rtfValue = -years; break;
                    default: rtfValue = -seconds; rtfUnit = 'second';
                }
            }
            
            try {
                const rtf = new Intl.RelativeTimeFormat(this.currentLang, { numeric: 'auto' });
                return rtf.format(rtfValue, rtfUnit);
            } catch (e) {
                // Fallback for browsers without RelativeTimeFormat
                return `${Math.abs(rtfValue)} ${rtfUnit}(s) ago`;
            }
        }

        /**
         * Get direction for current language
         * @returns {string} 'ltr' or 'rtl'
         */
        getDirection() {
            const rtlLanguages = ['ar', 'he', 'fa', 'ur'];
            return rtlLanguages.includes(this.currentLang) ? 'rtl' : 'ltr';
        }
    }

    // Create global instance
    const i18n = new I18nLoader();

    // Export
    window.I18nLoader = I18nLoader;
    window.i18n = i18n;
    
    // Shorthand function
    window.t = (key, params, count) => i18n.t(key, params, count);

})(window);
