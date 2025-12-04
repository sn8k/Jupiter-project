# Changelog - jupiter/web/js/auto_form.js

## v0.2.0
### Added
- Format validation for strings: email, url, uri, date-time, date, time, ipv4, ipv6, hostname
- Number validation: exclusiveMinimum, exclusiveMaximum, multipleOf
- Array validation: uniqueItems
- Enum validation for any type
- Custom validation function support via `x-validate` schema extension
- `_validateFormat()` method for string format validation

### Changed
- Enhanced `_validateField()` with comprehensive validation rules
- Improved validation error messages for all constraint types

## v0.1.0
### Added
- Initial release
- JSON Schema form generation
- Support for string, boolean, integer, number, array, object types
- Format-specific inputs (text, textarea, password, email, url, date, color)
- Boolean widgets (checkbox, toggle)
- Number widgets (input, range, stepper)
- Array widgets (multiple inputs, chips, select multiple)
- Nested fieldsets for objects
- Enum support (select, radio)
- Basic validation (required, minLength, maxLength, pattern, minimum, maximum, minItems, maxItems)
- Default values support
- Change/submit callbacks
- Field error display
- Reset to defaults
- Debounced input handling
