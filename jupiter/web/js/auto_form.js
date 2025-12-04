/**
 * Jupiter Auto-Form Generator
 * 
 * Version: 0.2.0
 * 
 * Generates HTML forms from JSON Schema definitions.
 * Used for plugin configuration forms in the Jupiter WebUI.
 * 
 * Supported JSON Schema types:
 * - string (text, textarea, password, email, url, date, color)
 * - boolean (checkbox, toggle)
 * - integer/number (input, range, stepper)
 * - array (multiple inputs, chips, select multiple)
 * - object (nested fieldsets)
 * - enum (select, radio)
 * 
 * Features:
 * - Validation based on schema
 * - Default values
 * - Conditional fields
 * - Custom widgets
 * - Accessibility (ARIA)
 */

(function(global) {
    'use strict';

    const VERSION = '0.2.0';

    // =============================================================================
    // CONFIGURATION
    // =============================================================================

    const defaultConfig = {
        idPrefix: 'autoform',
        classPrefix: 'af',
        labelPosition: 'top',  // 'top', 'left', 'inline'
        showDescriptions: true,
        showValidationErrors: true,
        showRequiredIndicator: true,
        requiredIndicator: '*',
        submitOnEnter: false,
        debounceMs: 300
    };

    // =============================================================================
    // FORM GENERATOR CLASS
    // =============================================================================

    class AutoForm {
        constructor(schema, options = {}) {
            this.schema = schema;
            this.options = { ...defaultConfig, ...options };
            this.values = {};
            this.errors = {};
            this.formElement = null;
            this.changeCallbacks = [];
            this.submitCallbacks = [];
            this._debounceTimers = {};
        }

        /**
         * Render the form
         */
        render(container = null) {
            const form = document.createElement('form');
            form.className = `${this.options.classPrefix}-form`;
            form.id = `${this.options.idPrefix}-form`;
            form.noValidate = true;  // Use custom validation

            // Render form fields from schema
            if (this.schema.properties) {
                Object.entries(this.schema.properties).forEach(([key, propSchema]) => {
                    const field = this._renderField(key, propSchema);
                    form.appendChild(field);
                });
            }

            // Submit handler
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                if (this.validate()) {
                    this._fireSubmit();
                }
            });

            this.formElement = form;

            // Apply initial values if provided
            if (this.options.initialValues) {
                this.setValues(this.options.initialValues);
            }

            // Append to container if provided
            if (container) {
                if (typeof container === 'string') {
                    container = document.querySelector(container);
                }
                if (container) {
                    container.appendChild(form);
                }
            }

            return form;
        }

        /**
         * Render a single field
         * @private
         */
        _renderField(key, schema) {
            const wrapper = document.createElement('div');
            wrapper.className = `${this.options.classPrefix}-field`;
            wrapper.dataset.fieldKey = key;

            const isRequired = this.schema.required?.includes(key);

            // Label
            if (schema.title || key) {
                const label = document.createElement('label');
                label.className = `${this.options.classPrefix}-label`;
                label.htmlFor = `${this.options.idPrefix}-${key}`;
                label.textContent = schema.title || this._humanizeKey(key);
                
                if (isRequired && this.options.showRequiredIndicator) {
                    const indicator = document.createElement('span');
                    indicator.className = `${this.options.classPrefix}-required`;
                    indicator.textContent = this.options.requiredIndicator;
                    indicator.setAttribute('aria-label', 'required');
                    label.appendChild(indicator);
                }
                
                wrapper.appendChild(label);
            }

            // Input element
            const input = this._createInput(key, schema, isRequired);
            wrapper.appendChild(input);

            // Description
            if (schema.description && this.options.showDescriptions) {
                const desc = document.createElement('div');
                desc.className = `${this.options.classPrefix}-description`;
                desc.id = `${this.options.idPrefix}-${key}-desc`;
                desc.textContent = schema.description;
                wrapper.appendChild(desc);
                input.setAttribute('aria-describedby', desc.id);
            }

            // Error container
            if (this.options.showValidationErrors) {
                const errorDiv = document.createElement('div');
                errorDiv.className = `${this.options.classPrefix}-error hidden`;
                errorDiv.id = `${this.options.idPrefix}-${key}-error`;
                errorDiv.setAttribute('role', 'alert');
                wrapper.appendChild(errorDiv);
            }

            return wrapper;
        }

        /**
         * Create an input element based on schema type
         * @private
         */
        _createInput(key, schema, isRequired) {
            const id = `${this.options.idPrefix}-${key}`;
            let input;

            // Handle enum (select or radio)
            if (schema.enum) {
                input = this._createEnumInput(key, schema, id);
            }
            // Handle type-based inputs
            else {
                switch (schema.type) {
                    case 'boolean':
                        input = this._createBooleanInput(key, schema, id);
                        break;
                    case 'integer':
                    case 'number':
                        input = this._createNumberInput(key, schema, id);
                        break;
                    case 'array':
                        input = this._createArrayInput(key, schema, id);
                        break;
                    case 'object':
                        input = this._createObjectInput(key, schema, id);
                        break;
                    case 'string':
                    default:
                        input = this._createStringInput(key, schema, id);
                        break;
                }
            }

            // Common attributes
            if (input.tagName !== 'FIELDSET') {
                input.name = key;
                if (isRequired) {
                    input.required = true;
                    input.setAttribute('aria-required', 'true');
                }
                if (schema.default !== undefined && !input.value) {
                    this._setInputValue(input, schema.default);
                }

                // Change handler
                const eventType = input.type === 'checkbox' || input.type === 'radio' ? 'change' : 'input';
                input.addEventListener(eventType, () => this._handleChange(key, input, schema));
            }

            return input;
        }

        /**
         * Create a string input
         * @private
         */
        _createStringInput(key, schema, id) {
            const format = schema.format || '';
            let input;

            // Textarea for long text
            if (schema.maxLength > 200 || format === 'textarea') {
                input = document.createElement('textarea');
                input.rows = schema.rows || 4;
            }
            // Specific formats
            else {
                input = document.createElement('input');
                switch (format) {
                    case 'email':
                        input.type = 'email';
                        break;
                    case 'uri':
                    case 'url':
                        input.type = 'url';
                        break;
                    case 'date':
                        input.type = 'date';
                        break;
                    case 'date-time':
                        input.type = 'datetime-local';
                        break;
                    case 'time':
                        input.type = 'time';
                        break;
                    case 'password':
                        input.type = 'password';
                        break;
                    case 'color':
                        input.type = 'color';
                        break;
                    default:
                        input.type = 'text';
                }
            }

            input.id = id;
            input.className = `${this.options.classPrefix}-input`;

            // Constraints
            if (schema.minLength !== undefined) input.minLength = schema.minLength;
            if (schema.maxLength !== undefined) input.maxLength = schema.maxLength;
            if (schema.pattern) input.pattern = schema.pattern;
            if (schema.placeholder) input.placeholder = schema.placeholder;

            return input;
        }

        /**
         * Create a boolean input (checkbox or toggle)
         * @private
         */
        _createBooleanInput(key, schema, id) {
            const wrapper = document.createElement('div');
            wrapper.className = `${this.options.classPrefix}-checkbox-wrapper`;

            const input = document.createElement('input');
            input.type = 'checkbox';
            input.id = id;
            input.className = `${this.options.classPrefix}-checkbox`;

            // Toggle style
            if (schema.format === 'toggle') {
                wrapper.className = `${this.options.classPrefix}-toggle-wrapper`;
                input.className = `${this.options.classPrefix}-toggle`;
            }

            wrapper.appendChild(input);
            return wrapper;
        }

        /**
         * Create a number input
         * @private
         */
        _createNumberInput(key, schema, id) {
            const input = document.createElement('input');
            input.id = id;
            input.className = `${this.options.classPrefix}-input`;

            // Range slider
            if (schema.format === 'range') {
                input.type = 'range';
            } else {
                input.type = 'number';
            }

            // Constraints
            if (schema.minimum !== undefined) input.min = schema.minimum;
            if (schema.maximum !== undefined) input.max = schema.maximum;
            if (schema.multipleOf !== undefined) input.step = schema.multipleOf;
            else if (schema.type === 'integer') input.step = 1;

            return input;
        }

        /**
         * Create an enum input (select or radio)
         * @private
         */
        _createEnumInput(key, schema, id) {
            // Use radio buttons for small enums
            if (schema.enum.length <= 4 && schema.format !== 'select') {
                return this._createRadioGroup(key, schema, id);
            }

            // Use select for larger enums
            const select = document.createElement('select');
            select.id = id;
            select.className = `${this.options.classPrefix}-select`;

            // Add empty option if not required
            if (!this.schema.required?.includes(key)) {
                const emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = '-- Select --';
                select.appendChild(emptyOpt);
            }

            schema.enum.forEach((value, idx) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = schema.enumNames?.[idx] || value;
                select.appendChild(option);
            });

            return select;
        }

        /**
         * Create a radio button group
         * @private
         */
        _createRadioGroup(key, schema, id) {
            const fieldset = document.createElement('fieldset');
            fieldset.className = `${this.options.classPrefix}-radio-group`;

            schema.enum.forEach((value, idx) => {
                const wrapper = document.createElement('div');
                wrapper.className = `${this.options.classPrefix}-radio-wrapper`;

                const input = document.createElement('input');
                input.type = 'radio';
                input.id = `${id}-${idx}`;
                input.name = key;
                input.value = value;
                input.className = `${this.options.classPrefix}-radio`;

                const label = document.createElement('label');
                label.htmlFor = `${id}-${idx}`;
                label.textContent = schema.enumNames?.[idx] || value;

                wrapper.appendChild(input);
                wrapper.appendChild(label);
                fieldset.appendChild(wrapper);

                // Change handler for radio
                input.addEventListener('change', () => this._handleChange(key, input, schema));
            });

            return fieldset;
        }

        /**
         * Create an array input
         * @private
         */
        _createArrayInput(key, schema, id) {
            const wrapper = document.createElement('div');
            wrapper.id = id;
            wrapper.className = `${this.options.classPrefix}-array`;
            wrapper.dataset.key = key;

            // If items have enum, use multi-select or chips
            if (schema.items?.enum) {
                return this._createMultiSelect(key, schema, id);
            }

            // Otherwise, use dynamic list
            const listContainer = document.createElement('div');
            listContainer.className = `${this.options.classPrefix}-array-items`;
            wrapper.appendChild(listContainer);

            const addButton = document.createElement('button');
            addButton.type = 'button';
            addButton.className = `btn btn-secondary ${this.options.classPrefix}-array-add`;
            addButton.textContent = '+ Add';
            addButton.onclick = () => this._addArrayItem(key, schema, listContainer);
            wrapper.appendChild(addButton);

            return wrapper;
        }

        /**
         * Create a multi-select input
         * @private
         */
        _createMultiSelect(key, schema, id) {
            const select = document.createElement('select');
            select.id = id;
            select.name = key;
            select.multiple = true;
            select.className = `${this.options.classPrefix}-multiselect`;

            schema.items.enum.forEach((value, idx) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = schema.items.enumNames?.[idx] || value;
                select.appendChild(option);
            });

            select.addEventListener('change', () => this._handleChange(key, select, schema));

            return select;
        }

        /**
         * Add an item to array input
         * @private
         */
        _addArrayItem(key, schema, container, value = '') {
            const itemWrapper = document.createElement('div');
            itemWrapper.className = `${this.options.classPrefix}-array-item`;

            const input = document.createElement('input');
            input.type = 'text';
            input.className = `${this.options.classPrefix}-input`;
            input.value = value;
            input.dataset.arrayKey = key;
            input.addEventListener('input', () => this._handleArrayChange(key));

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = `btn btn-icon ${this.options.classPrefix}-array-remove`;
            removeBtn.textContent = '×';
            removeBtn.onclick = () => {
                itemWrapper.remove();
                this._handleArrayChange(key);
            };

            itemWrapper.appendChild(input);
            itemWrapper.appendChild(removeBtn);
            container.appendChild(itemWrapper);
        }

        /**
         * Create an object input (nested fieldset)
         * @private
         */
        _createObjectInput(key, schema, id) {
            const fieldset = document.createElement('fieldset');
            fieldset.id = id;
            fieldset.className = `${this.options.classPrefix}-object`;

            if (schema.title) {
                const legend = document.createElement('legend');
                legend.textContent = schema.title;
                fieldset.appendChild(legend);
            }

            // Recursively render properties
            if (schema.properties) {
                Object.entries(schema.properties).forEach(([propKey, propSchema]) => {
                    const nestedKey = `${key}.${propKey}`;
                    const field = this._renderField(nestedKey, propSchema);
                    fieldset.appendChild(field);
                });
            }

            return fieldset;
        }

        /**
         * Handle input change
         * @private
         */
        _handleChange(key, input, schema) {
            // Debounce
            clearTimeout(this._debounceTimers[key]);
            this._debounceTimers[key] = setTimeout(() => {
                const value = this._getInputValue(input, schema);
                this._setNestedValue(this.values, key, value);
                this._validateField(key, value, schema);
                this._fireChange(key, value);
            }, this.options.debounceMs);
        }

        /**
         * Handle array input change
         * @private
         */
        _handleArrayChange(key) {
            const inputs = this.formElement.querySelectorAll(`input[data-array-key="${key}"]`);
            const values = Array.from(inputs).map(i => i.value).filter(v => v);
            this._setNestedValue(this.values, key, values);
            this._fireChange(key, values);
        }

        /**
         * Get value from input
         * @private
         */
        _getInputValue(input, schema) {
            if (input.type === 'checkbox') {
                return input.checked;
            }
            if (input.type === 'number' || input.type === 'range') {
                return input.value ? Number(input.value) : null;
            }
            if (input.multiple) {
                return Array.from(input.selectedOptions).map(o => o.value);
            }
            return input.value;
        }

        /**
         * Set value to input
         * @private
         */
        _setInputValue(input, value) {
            if (input.type === 'checkbox') {
                input.checked = Boolean(value);
            } else if (input.multiple && Array.isArray(value)) {
                Array.from(input.options).forEach(opt => {
                    opt.selected = value.includes(opt.value);
                });
            } else {
                input.value = value ?? '';
            }
        }

        /**
         * Set nested object value by dot-notation key
         * @private
         */
        _setNestedValue(obj, key, value) {
            const keys = key.split('.');
            let current = obj;
            for (let i = 0; i < keys.length - 1; i++) {
                if (!current[keys[i]]) current[keys[i]] = {};
                current = current[keys[i]];
            }
            current[keys[keys.length - 1]] = value;
        }

        /**
         * Get nested object value by dot-notation key
         * @private
         */
        _getNestedValue(obj, key) {
            return key.split('.').reduce((o, k) => o?.[k], obj);
        }

        /**
         * Humanize a key name
         * @private
         */
        _humanizeKey(key) {
            return key
                .split(/[._-]/)
                .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                .join(' ');
        }

        /**
         * Validate a single field
         * @private
         */
        _validateField(key, value, schema) {
            const errors = [];

            // Required
            if (this.schema.required?.includes(key.split('.')[0])) {
                if (value === null || value === undefined || value === '' || 
                    (Array.isArray(value) && value.length === 0)) {
                    errors.push('This field is required');
                }
            }

            // Type-specific validation
            if (value !== null && value !== undefined && value !== '') {
                // String constraints
                if (schema.type === 'string') {
                    if (schema.minLength && value.length < schema.minLength) {
                        errors.push(`Minimum length is ${schema.minLength}`);
                    }
                    if (schema.maxLength && value.length > schema.maxLength) {
                        errors.push(`Maximum length is ${schema.maxLength}`);
                    }
                    if (schema.pattern && !new RegExp(schema.pattern).test(value)) {
                        errors.push(schema.patternError || 'Invalid format');
                    }
                    
                    // Format validation
                    if (schema.format) {
                        const formatError = this._validateFormat(value, schema.format);
                        if (formatError) {
                            errors.push(formatError);
                        }
                    }
                }

                // Number constraints
                if (schema.type === 'number' || schema.type === 'integer') {
                    if (schema.minimum !== undefined && value < schema.minimum) {
                        errors.push(`Minimum value is ${schema.minimum}`);
                    }
                    if (schema.maximum !== undefined && value > schema.maximum) {
                        errors.push(`Maximum value is ${schema.maximum}`);
                    }
                    if (schema.exclusiveMinimum !== undefined && value <= schema.exclusiveMinimum) {
                        errors.push(`Value must be greater than ${schema.exclusiveMinimum}`);
                    }
                    if (schema.exclusiveMaximum !== undefined && value >= schema.exclusiveMaximum) {
                        errors.push(`Value must be less than ${schema.exclusiveMaximum}`);
                    }
                    if (schema.multipleOf !== undefined && value % schema.multipleOf !== 0) {
                        errors.push(`Value must be a multiple of ${schema.multipleOf}`);
                    }
                }

                // Array constraints
                if (schema.type === 'array' && Array.isArray(value)) {
                    if (schema.minItems && value.length < schema.minItems) {
                        errors.push(`At least ${schema.minItems} items required`);
                    }
                    if (schema.maxItems && value.length > schema.maxItems) {
                        errors.push(`Maximum ${schema.maxItems} items allowed`);
                    }
                    if (schema.uniqueItems && new Set(value).size !== value.length) {
                        errors.push('All items must be unique');
                    }
                }
                
                // Enum validation
                if (schema.enum && !schema.enum.includes(value)) {
                    errors.push(`Value must be one of: ${schema.enum.join(', ')}`);
                }
            }

            // Custom validation function
            if (schema['x-validate'] && typeof schema['x-validate'] === 'function') {
                const customError = schema['x-validate'](value, this.values);
                if (customError) {
                    errors.push(customError);
                }
            }

            // Update error state
            if (errors.length > 0) {
                this.errors[key] = errors;
                this._showFieldError(key, errors[0]);
            } else {
                delete this.errors[key];
                this._hideFieldError(key);
            }

            return errors.length === 0;
        }

        /**
         * Validate string format
         * @private
         */
        _validateFormat(value, format) {
            const formats = {
                email: {
                    regex: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    error: 'Invalid email address'
                },
                url: {
                    regex: /^https?:\/\/[^\s]+$/,
                    error: 'Invalid URL (must start with http:// or https://)'
                },
                uri: {
                    regex: /^[a-z][a-z0-9+.-]*:/,
                    error: 'Invalid URI'
                },
                'date-time': {
                    regex: /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/,
                    error: 'Invalid date-time format (use ISO 8601)'
                },
                date: {
                    regex: /^\d{4}-\d{2}-\d{2}$/,
                    error: 'Invalid date format (use YYYY-MM-DD)'
                },
                time: {
                    regex: /^\d{2}:\d{2}(:\d{2})?$/,
                    error: 'Invalid time format (use HH:MM or HH:MM:SS)'
                },
                ipv4: {
                    regex: /^(\d{1,3}\.){3}\d{1,3}$/,
                    error: 'Invalid IPv4 address'
                },
                ipv6: {
                    regex: /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/,
                    error: 'Invalid IPv6 address'
                },
                hostname: {
                    regex: /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/,
                    error: 'Invalid hostname'
                }
            };

            const formatDef = formats[format];
            if (formatDef && !formatDef.regex.test(value)) {
                return formatDef.error;
            }
            
            return null;
        }

        /**
         * Show field error
         * @private
         */
        _showFieldError(key, message) {
            const errorEl = document.getElementById(`${this.options.idPrefix}-${key}-error`);
            if (errorEl) {
                errorEl.textContent = message;
                errorEl.classList.remove('hidden');
            }
            const field = this.formElement.querySelector(`[data-field-key="${key}"]`);
            if (field) {
                field.classList.add(`${this.options.classPrefix}-has-error`);
            }
        }

        /**
         * Hide field error
         * @private
         */
        _hideFieldError(key) {
            const errorEl = document.getElementById(`${this.options.idPrefix}-${key}-error`);
            if (errorEl) {
                errorEl.textContent = '';
                errorEl.classList.add('hidden');
            }
            const field = this.formElement.querySelector(`[data-field-key="${key}"]`);
            if (field) {
                field.classList.remove(`${this.options.classPrefix}-has-error`);
            }
        }

        /**
         * Validate all fields
         */
        validate() {
            let isValid = true;
            
            if (this.schema.properties) {
                Object.entries(this.schema.properties).forEach(([key, propSchema]) => {
                    const value = this._getNestedValue(this.values, key);
                    if (!this._validateField(key, value, propSchema)) {
                        isValid = false;
                    }
                });
            }

            return isValid;
        }

        /**
         * Get current form values
         */
        getValues() {
            return { ...this.values };
        }

        /**
         * Set form values
         */
        setValues(values) {
            this.values = { ...values };
            
            // Update form inputs
            if (this.formElement) {
                Object.entries(values).forEach(([key, value]) => {
                    const input = this.formElement.querySelector(`#${this.options.idPrefix}-${key}`);
                    if (input) {
                        this._setInputValue(input, value);
                    }
                });
            }
        }

        /**
         * Reset form to defaults
         */
        reset() {
            this.values = {};
            this.errors = {};
            
            if (this.formElement) {
                this.formElement.reset();
                
                // Apply default values
                if (this.schema.properties) {
                    Object.entries(this.schema.properties).forEach(([key, schema]) => {
                        if (schema.default !== undefined) {
                            const input = this.formElement.querySelector(`#${this.options.idPrefix}-${key}`);
                            if (input) {
                                this._setInputValue(input, schema.default);
                                this.values[key] = schema.default;
                            }
                        }
                    });
                }
            }
        }

        /**
         * Register change callback
         */
        onChange(callback) {
            if (typeof callback === 'function') {
                this.changeCallbacks.push(callback);
            }
            return this;
        }

        /**
         * Register submit callback
         */
        onSubmit(callback) {
            if (typeof callback === 'function') {
                this.submitCallbacks.push(callback);
            }
            return this;
        }

        /**
         * Fire change event
         * @private
         */
        _fireChange(key, value) {
            this.changeCallbacks.forEach(cb => {
                try {
                    cb(key, value, this.values);
                } catch (e) {
                    console.error('[AutoForm] Change callback error:', e);
                }
            });
        }

        /**
         * Fire submit event
         * @private
         */
        _fireSubmit() {
            this.submitCallbacks.forEach(cb => {
                try {
                    cb(this.values);
                } catch (e) {
                    console.error('[AutoForm] Submit callback error:', e);
                }
            });
        }

        /**
         * Destroy the form
         */
        destroy() {
            if (this.formElement && this.formElement.parentNode) {
                this.formElement.parentNode.removeChild(this.formElement);
            }
            this.formElement = null;
            this.changeCallbacks = [];
            this.submitCallbacks = [];
        }
    }

    // =============================================================================
    // FACTORY FUNCTION
    // =============================================================================

    /**
     * Create and render an auto-form
     */
    function createAutoForm(schema, container, options = {}) {
        const form = new AutoForm(schema, options);
        form.render(container);
        return form;
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

    const autoForm = {
        AutoForm,
        create: createAutoForm,
        getVersion
    };

    // Export globally
    global.jupiterAutoForm = autoForm;

    // Also export as ES module if supported
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = autoForm;
    }

})(typeof window !== 'undefined' ? window : this);
